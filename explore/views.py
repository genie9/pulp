# This file is part of PULP.
#
# PULP is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PULP is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PULP.  If not, see <http://www.gnu.org/licenses/>.

from django.db.models import Q
from django.shortcuts import render

from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView  # class-based views
from rest_framework.decorators import api_view  # for function-based views

from explore.models import Article, ArticleTFIDF, Experiment, ExperimentIteration, ArticleFeedback, User, TopicWeight, \
    ArticleSection
from explore.serializers import ArticleSerializer
from explore.utils import *

from nltk.stem import SnowballStemmer
from sklearn.preprocessing import normalize
from scipy.sparse.linalg import spsolve

import collections
import sys
import random
import operator
import numpy
import json
import time
import os.path
import datetime
import re

# from profilehooks import profile, coverage, timecall


DEFAULT_NUM_ARTICLES = 10


# class UserViewSet(viewsets.ModelViewSet):
#    queryset = User.objects.all()
#    serializer_class = UserSerializer

class PulpException(Exception):
    pass


class GetArticle(generics.RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer


# class GetArticleOld(APIView) :
#    def get(self, request, article_id) :
#        try :
#            article = Article.objects.get(id=article_id)
#
#        except Article.DoesNotExist :
#            return Response(status=status.HTTP_404_NOT_FOUND)
#
#        serializer = ArticleSerializer(article)
#        return Response(serializer.data)

@api_view(['GET'])
def logout_view(request):
    # logout(request)
    return Response(status=status.HTTP_200_OK)


# print "caching timestamps..."
TIMESTAMPS = None  # dict([ (a.id - 1, a.date) for a in Article.objects.all() ]) # -1 because numpy is zero indexed


def get_articles(method, experiment, start_index, num_articles):
    if method in ('bm25', 'okapibm25'):
        return get_articles_bm25(experiment, start_index, num_articles)

    elif method in ('linrel',):
        return get_articles_linrel(experiment, start_index, num_articles)

    elif method in ('linrel_positive',):
        return get_articles_linrel_positive(experiment, start_index, num_articles)

    else:
        assert False, "unknown algorithm requested (%s)" % (method)


badchars_pat = re.compile("[^a-zA-Z\s]")


# query terms - a list of stemmed query words
# n - the number of articles to return
# @timecall(immediate=True)
def get_articles_bm25(exp, start_index, num_articles):  # query_terms, n, from_date, to_date, e) :
    bm25 = load_sparse_bm25()
    features = load_features_bm25()

    query = badchars_pat.sub(' ', exp.query).lower()

    stemmer = SnowballStemmer('english')
    query_terms = [stemmer.stem(term) for term in query.split()]

    if not len(query_terms):
        raise PulpException("query string (\"%s\") contains no query terms" % (exp.query))

    from_date = exp.from_date
    to_date = exp.to_date

    tmp = {}

    for qt in query_terms:
        if qt not in features:
            continue

        findex = features[qt]

        for aindex in numpy.nonzero(bm25[:, findex])[0]:
            akey = aindex.item()
            if akey not in tmp:
                tmp[akey] = 0.0

            tmp[akey] += bm25[aindex, findex]

    ranking = sorted(tmp.items(), key=lambda x: x[1], reverse=True)

    # to support positive feedback only linrel, okapiBM25 might be
    # called after the first iteration
    articles_obj = ArticleFeedback.objects.filter(experiment=exp).exclude(selected=None)
    articles = [a.article.id - 1 for a in articles_obj]

    print articles

    # ver.3
    # find top n articles in date range
    top_ids = []
    for i in ranking:
        if (i[0] not in articles) and ((not TIMESTAMPS) or (from_date < TIMESTAMPS[i[0]] <= to_date)):
            top_ids.append(i[0] + 1)  # +1 because db is one indexed

            if len(top_ids) == (start_index + num_articles):
                break

    top_ids = top_ids[-num_articles:]

    # ver.1
    # return [ articles[r[0]] for r in ranking[:n] ]

    # ver.2
    # id2article = dict([ (a.id, a) for a in Article.objects.filter(pk__in=[ r[0]+1 for r in ranking[:n] ]) ])
    # top_articles = [ id2article[i[0]+1] for i in ranking[:n] ]

    # ver.3
    id2article = dict([(a.id, a) for a in Article.objects.filter(pk__in=top_ids)])
    top_articles = [id2article[i] for i in top_ids]

    return top_articles


print "loading sparse linrel..."
X = load_sparse_linrel()


def linrel(articles, feedback, data, start, n, from_date, to_date, mew=1.0, exploration_rate=1.0):
    assert len(articles) == len(feedback), "articles and feedback are not the same length"

    X = data

    num_articles = X.shape[0]
    num_features = X.shape[1]

    X_t = X[numpy.array(articles)]
    X_tt = X_t.transpose()

    I = mew * scipy.sparse.identity(num_features, format='dia')

    W = spsolve((X_tt * X_t) + I, X_tt)
    A = X * W

    Y_t = numpy.matrix(feedback).transpose()

    tmpA = numpy.array(A.todense())
    normL2 = numpy.matrix(numpy.sqrt(numpy.sum(tmpA * tmpA, axis=1))).transpose()

    # W * Y_t is the keyword weights
    K = W * Y_t

    mean = A * Y_t
    variance = (exploration_rate / 2.0) * normL2
    I_t = mean + variance

    linrel_ordered = numpy.argsort(I_t.transpose()[0]).tolist()[0]
    top_n = []

    for i in linrel_ordered[::-1]:
        # if i not in articles :
        if (i not in articles) and ((not TIMESTAMPS) or (from_date < TIMESTAMPS[i] <= to_date)):
            top_n.append(i)

        if len(top_n) == (start + n):
            break

    top_n = top_n[-n:]

    return top_n, \
           mean[numpy.array(top_n)].transpose().tolist()[0], \
           variance[numpy.array(top_n)].transpose().tolist()[0], \
           K


def linrel_positive_feedback_only(articles, feedback, data, start, n, from_date, to_date, mew=1.0,
                                  exploration_rate=1.0):
    assert len(articles) == len(feedback), "articles and feedback are not the same length"

    X = data

    num_articles = X.shape[0]
    num_features = X.shape[1]

    # positive_articles = [ articles[i] for i,fb in enumerate(feedback) if fb == 1 ]

    # print feedback
    # print positive_articles

    # if len(positive_articles) < 2 :
    #    raise PulpException("need feedback on 2 or more articles for linrel to work with only positive feedback, %d provided" % (len(positive_articles)))

    X_t = X[numpy.array(articles)]
    # X_t = X[ numpy.array(positive_articles) ]
    X_tt = X_t.transpose()

    I = mew * scipy.sparse.identity(num_features, format='dia')

    W = spsolve((X_tt * X_t) + I, X_tt)
    A = X * W

    Y_t = numpy.matrix(feedback).transpose()
    # Y_t = numpy.matrix([1] * int(sum(feedback))).transpose()

    tmpA = numpy.array(A.todense())
    normL2 = numpy.matrix(numpy.sqrt(numpy.sum(tmpA * tmpA, axis=1))).transpose()

    # W * Y_t is the keyword weights
    K = W * Y_t

    mean = A * Y_t
    variance = (exploration_rate / 2.0) * normL2
    I_t = mean + variance

    linrel_ordered = numpy.argsort(I_t.transpose()[0]).tolist()[0]
    top_n = []

    for i in linrel_ordered[::-1]:
        # if i not in articles :
        if (i not in articles) and ((not TIMESTAMPS) or (from_date < TIMESTAMPS[i] <= to_date)):
            top_n.append(i)

        if len(top_n) == (start + n):
            break

    top_n = top_n[-n:]

    return top_n, \
           mean[numpy.array(top_n)].transpose().tolist()[0], \
           variance[numpy.array(top_n)].transpose().tolist()[0], \
           K


def get_keyword_stats(articles, keyword_weights):
    K = keyword_weights
    top_articles = articles

    # XXX this is temporary, for experimenting only
    #     and needs to be stored in the database
    stemmer = SnowballStemmer('english')

    used_keywords = collections.defaultdict(list)

    for i in top_articles:
        for word, stem in [(word, stemmer.stem(word)) for word in i.title.split() + i.abstract.split()]:
            used_keywords[stem].append(word)

    keyword_stats = {}
    features = load_features_linrel()

    for word in used_keywords:
        if word not in features:
            continue

        index = features[word]
        value = K[int(index), 0] ** 2

        for key in used_keywords[word]:
            keyword_stats[key] = value

    keyword_sum = sum(keyword_stats.values())

    # if no articles are selected (feedback = [0,0,0,... ])
    # then this can divide by zero
    if keyword_sum:
        for i in keyword_stats:
            keyword_stats[i] /= keyword_sum

    return keyword_stats


def get_stems(articles):
    stems = collections.defaultdict(list)

    stopwords = get_stop_words()
    stemmer = SnowballStemmer('english')

    for i in articles:
        for word, stem in [(word, stemmer.stem(word)) for word in clean_text(i.title + ' ' + i.abstract).split() if
                           word not in stopwords]:
            if stem not in stems[i.id]:
                stems[i.id].append(stem)

    for k in stems:
        stems[k].sort()

    return dict(stems)


def get_article_stats(articles, exploitation, exploration):
    article_stats = {}

    for index, article_id in enumerate(articles):
        article_stats[article_id] = (exploitation[index], exploration[index])

    return article_stats


# @timecall(immediate=True)
# @profile
def get_top_articles_linrel(e, start, count, exploration):
    global X

    articles_obj = ArticleFeedback.objects.filter(experiment=e).exclude(selected=None)
    articles_npid = [a.article.id - 1 for a in articles_obj]  # database is 1-indexed, numpy is 0-indexed
    feedback = [1.0 if a.selected else 0.0 for a in articles_obj]
    data = X

    articles_new_npid, mean, variance, kw_weights = linrel_positive_feedback_only(  # linrel(
        articles_npid,
        feedback,
        data,
        start,
        count,
        e.from_date,
        e.to_date,
        exploration_rate=exploration)

    articles_new_dbid = [i + 1 for i in articles_new_npid]  # database is 1-indexed, numpy is 0-indexed
    articles_new_obj = Article.objects.filter(pk__in=articles_new_dbid)

    # everything comes out of the database sorted by id...
    tmp = dict([(a.id, a) for a in articles_new_obj])

    return [tmp[id] for id in articles_new_dbid], \
           get_keyword_stats(articles_new_obj, kw_weights), \
           get_article_stats(articles_new_dbid, mean, variance), \
           get_stems(articles_new_obj)


def get_running_experiments(user):
    return Experiment.objects.filter(user=user, state=Experiment.RUNNING)


# def create_experiment(sid, user, num_documents) :
#    get_running_experiments(sid).update(state=Experiment.ERROR)
#
#    e = Experiment()
#
#    e.sessionid = sid
#    e.number_of_documents = num_documents
#    #e.user = user
#
#    e.save()
#
#    return e

def get_experiment(user):
    e = get_running_experiments(user)

    if len(e) != 1:
        e.update(state=Experiment.ERROR)
        return None

    return e[0]


def create_iteration(experiment, articles):
    ei = ExperimentIteration()
    ei.experiment = experiment
    ei.iteration = experiment.number_of_iterations
    ei.save()

    for article in articles:
        afb = ArticleFeedback()
        afb.article = article
        afb.experiment = experiment
        afb.iteration = ei
        afb.save()

    return ei


def get_last_iteration(e):
    return ExperimentIteration.objects.get(experiment=e, iteration=e.number_of_iterations - 1)


def add_feedback(ei, articles, clickdata, seendata):
    feedback = ArticleFeedback.objects.filter(iteration=ei)

    clicks = dict([(c['id'], (c['reading_started'], c['reading_ended'])) for c in clickdata])

    for fb in feedback:
        print "saving clicked=%s for %s" % (str(fb.article.id in articles), str(fb.article.id))
        fb.selected = fb.article.id in articles
        fb.clicked = fb.article.id in clicks
        fb.seen = fb.article.id in seendata

        if fb.clicked:
            fb.reading_start, fb.reading_end = clicks[fb.article.id]

        fb.save()


def get_unseen_articles(e):
    return Article.objects.exclude(pk__in=[a.article.id for a in ArticleFeedback.objects.filter(experiment=e)])


@api_view(['GET'])
def textual_query(request):
    if request.method == 'GET':
        # experiments are started implicitly with a text query
        # and experiments are tagged with the session id
        #        request.session.flush()
        # print request.session.session_key
        print json.dumps(request.GET, sort_keys=True, indent=4, separators=(',', ': '))

        # get parameters from url
        # q : query string
        if 'q' not in request.GET:  # or 'participant_id' not in request.GET :
            return Response(status=status.HTTP_400_BAD_REQUEST)

        query_string = request.GET['q']

        if ('participant_id' in request.GET) and request.GET['participant_id']:
            participant_id = request.GET['participant_id']
        else:
            request.session.flush()
            participant_id = request.session.session_key

        print "participant =", participant_id

        try:
            user = User.objects.get(username=participant_id)

        except User.DoesNotExist:
            user = User()
            user.username = participant_id
            user.save()
            # return Response(status=status.HTTP_400_BAD_REQUEST)

        # article-count : number of articles to return
        num_articles = int(request.GET.get('article-count', DEFAULT_NUM_ARTICLES))
        num_topic_articles = int(request.GET.get('topic-count', 100))

        if num_topic_articles < num_articles:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # from_year and to_year to run the query over
        from_year = datetime.date(request.GET.get('from_year', 1900), 1, 1)
        to_year = datetime.date(request.GET.get('to_year', 2100), 12, 31)

        print "article-count: %d" % (num_articles)

        # create new experiment
        e = get_experiment(user)

        if not e:
            e = Experiment()
            e.user = user
            # e.task_type             = Experiment.EXPLORATORY
            # e.study_type            = 1 # full system
            # e.base_exploration_rate = 1.0
            e.exploration_rate = 1.0
            e.number_of_documents = num_articles
            e.query = query_string
            e.from_date = from_year
            e.to_date = to_year
            e.save()

        # e.query = query_string
        # e.number_of_documents = num_articles
        # e.from_date = from_year
        # e.to_date = to_year

        try:
            # get documents with okapi bm25-based ranking
            topic_articles = get_articles("bm25", e, 0, num_topic_articles)

        except PulpException, pe:
            print "ERROR", str(pe)
            return Response(status=status.HTTP_400_BAD_REQUEST)

        num_articles = e.number_of_documents
        articles = topic_articles[:num_articles]

        # add random articles if we don't have enough
        fill_count = num_articles - len(articles)
        if fill_count:
            print "only %d articles found, adding %d random ones" % (len(articles), fill_count)
            articles += random.sample(Article.objects.all(), fill_count)

        # create new experiment iteration
        # save new documents to current experiment iteration
        create_iteration(e, articles)
        e.number_of_iterations += 1
        e.save()

        serializer = ArticleSerializer(articles, many=True)
        return Response({'articles': serializer.data,
                         'sections': get_sections(topic_articles),
                         'topics': get_topics(topic_articles)})


def store_feedback(e, post):
    ei = get_last_iteration(e)
    selected_documents = [int(i) for i in post['selected']]
    print selected_documents

    #    if ei.iteration == 0 :
    #        print "exploratory = '%s'" % post.get('exploratory', 0)
    #        #e.classifier = int(post.get('exploratory', 0)) == 1
    #        e.classifier = True
    #
    #        if e.classifier and e.study_type == 1 :
    #            print "USING EXPLORATION (classifier = %s, study_type = %s)"
    #                   % (str(e.classifier), 'full' if e.study_type == 1 else 'baseline')
    #            e.exploration_rate = e.base_exploration_rate
    #        else :
    #            print "NOT USING EXPLORATION (classifier = %s, study_type = %s)"
    #                   % (str(e.classifier), 'full' if e.study_type == 1 else 'baseline')
    #
    #    print "exploration rate set to %.2f" % e.exploration_rate

    # add selected documents to previous experiment iteration
    add_feedback(ei, selected_documents, post['clicked'], post['seen'])


@api_view(['POST'])
def selection_query(request):
    if request.method == 'POST':
        post = json.loads(request.body)

        print json.dumps(post, sort_keys=True, indent=4, separators=(',', ': '))

        start_time = time.time()

        # get user object
        if ('participant_id' in post) and post['participant_id']:
            participant_id = post['participant_id']
        else:
            participant_id = request.session.session_key

        print "participant =", participant_id

        try:
            user = User.objects.get(username=participant_id)

        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # get experiment object
        e = get_experiment(user)

        try:
            store_feedback(e, post)

        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        num_topic_articles = int(request.GET.get('topic-count', 100))

        if num_topic_articles < e.number_of_documents:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # # get previous experiment iteration
        #        try :
        #            ei = get_last_iteration(e)
        #
        #        except ExperimentIteration.DoesNotExist :
        #            return Response(status=status.HTTP_400_BAD_REQUEST)
        #
        #        # get parameters from url
        #        # ?id=x&id=y&id=z
        #        try :
        #            selected_documents = [ int(i) for i in post['selected'] ]
        #
        #        except ValueError :
        #            return Response(status=status.HTTP_400_BAD_REQUEST)
        #
        #        print selected_documents
        #
        #        # only sent in iteration 1
        #        if ei.iteration == 0 :
        #            try :
        #                print "exploratory =", post['exploratory']
        #                apply_exploration = post['exploratory'] == "1"
        #
        #            except :
        #                return Response(status=status.HTTP_400_BAD_REQUEST)
        #
        #            if apply_exploration :
        #                e.exploration_rate = e.base_exploration_rate
        #
        #        print "exploration rate set to %.2f" % e.exploration_rate
        #
        #        # add selected documents to previous experiment iteration
        #        add_feedback(ei, selected_documents, post['clicked'], post['seen'])

        # ver.1
        # rand_articles, keywords, article_stats, stems = get_top_articles_linrel(e, 0, e.number_of_documents, e.exploration_rate)

        # ver.2
        # topic_articles, keywords, article_stats, stems = get_top_articles_linrel(e, 0, num_topic_articles, e.exploration_rate)
        # rand_articles = topic_articles[:e.number_of_documents]

        # ver.3
        print "exploration rate = %f" % e.exploration_rate
        try:
            topic_articles, keywords, article_stats, stems = get_top_articles_linrel(e, 0, num_topic_articles,
                                                                                     e.exploration_rate)
            rand_articles = topic_articles[:e.number_of_documents]

        except PulpException, pe:
            print "ERROR", str(pe)

            # an exception was thrown because we need feedback on at least two
            # articles to run linrel with only positive feedback, fall back to
            # okapiBM25 ranking

            topic_articles = get_articles("bm25", e, 0, num_topic_articles)
            print "bm25 returned %d" % len(topic_articles)

            rand_articles = topic_articles[:e.number_of_documents]

            create_iteration(e, rand_articles)
            e.number_of_iterations += 1
            e.save()

            serializer = ArticleSerializer(rand_articles, many=True)

            print "returning %d articles" % len(rand_articles)

            return Response({'articles': serializer.data,
                             'keywords': {},
                             'sections': get_sections(topic_articles),
                             'topics': get_topics(topic_articles)})

        print "%d articles (%s)" % (len(rand_articles), ','.join([str(a.id) for a in rand_articles]))

        # create new experiment iteration
        # save new documents to current experiment iteration
        create_iteration(e, rand_articles)
        e.number_of_iterations += 1
        e.save()

        # response to client
        serializer = ArticleSerializer(rand_articles, many=True)
        article_data = serializer.data
        for i in article_data:
            mean, var = article_stats[i['id']]
            i['mean'] = mean
            i['variance'] = var

        print time.time() - start_time

        return Response({'articles': article_data,
                         'keywords': keywords,
                         'sections': get_sections(topic_articles),
                         'topics': get_topics(topic_articles)})


@api_view(['GET'])
def system_state(request):
    return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        e = get_experiment(request.session.session_key)
        try:
            start = int(request.GET['start'])
            count = int(request.GET['count'])

        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        print "start = %d, count = %d" % (start, count)

        articles, keyword_stats, article_stats, stems = get_top_articles_linrel(e, start, count, e.exploration_rate)
        serializer = ArticleSerializer(articles, many=True)

        for i in serializer.data:
            i['stemming'] = stems[i['id']]

        return Response({'article_data': article_stats,
                         'keywords': keyword_stats,
                         'all_articles': serializer.data})


@api_view(['POST'])
def end_search(request):
    if request.method == 'POST':
        post = json.loads(request.body)

        if 'participant_id' not in post:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        participant_id = post['participant_id']

        try:
            user = User.objects.get(username=participant_id)

        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        e = get_experiment(user)

        try:
            store_feedback(e, post)

        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        e.state = Experiment.COMPLETE
        e.save()

        return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def index(request):
    return render(request, 'index.html')


@api_view(['GET'])
def visualization(request):
    return render(request, 'visualization.html')


@api_view(['GET'])
def setup_experiment(request):
    # /setup?participant_id=1234&task_type=0&exploration_rate=1&task_order=1

    print json.dumps(request.GET, sort_keys=True, indent=4, separators=(',', ': '))

    try:
        participant_id = request.GET['participant_id']
        #        experiment_id       = int(request.GET['experiment_id'])
        #        task_type           = int(request.GET['task_type'])
        exploration_rate = float(request.GET['exploration_rate'])
        num_documents = int(request.GET['article_count'])
        query = request.GET['q']

    except:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # if task_type not in (0, 1) :
    #        return Response(status=status.HTTP_400_BAD_REQUEST)

    if exploration_rate < 0.0 or num_documents < 1 or query == "":
        return Response(status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=participant_id)

    except User.DoesNotExist:
        user = User()
        user.username = participant_id
        user.save()

    # check if there are any running experiments
    # and set them to ERROR
    Experiment.objects.filter(user=user, state=Experiment.RUNNING).update(state=Experiment.ERROR)

    # create experiment
    e = Experiment()
    e.user = user
    # e.task_type             = Experiment.EXPLORATORY #if task_type == 0 else Experiment.LOOKUP
    # e.study_type            = 0 #experiment_id
    # e.number_of_documents   = DEFAULT_NUM_ARTICLES
    # e.base_exploration_rate = exploration_rate
    e.exploration_rate = exploration_rate
    e.number_of_documents = num_documents
    e.query = query
    e.save()

    # print "STUDY TYPE: %s" % ("full system" if e.study_type == 1 else "baseline")
    # print "TASK TYPE: %s" % ("exploratory" if e.task_type == Experiment.EXPLORATORY else "lookup")
    # print "EXPLORATION RATE: %.2f" % e.base_exploration_rate

    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
def experiment_ratings(request):
    ratings = json.loads(request.body)

    if ('participant_id' not in ratings or 'task_type' not in ratings or 'study_type' not in ratings
            or 'ratings' not in ratings or 'classifier_value' not in ratings or 'query' not in ratings):
        return Response(status=status.HTTP_400_BAD_REQUEST)

    ratings_file = open(os.path.dirname(__file__) + '/../ratings.json', 'r')
    ratings_arr = ratings_file.read()
    ratings_file.close()

    ratings_file = open(os.path.dirname(__file__) + '/../ratings.json', 'w')

    if not ratings_arr:
        ratings_arr = []
    else:
        ratings_arr = json.loads(ratings_arr)

    ratings_arr.append({
        'participant_id': ratings['participant_id'],
        'task_type': ratings['task_type'],
        'study_type': ratings['study_type'],
        'classifier_value': ratings['classifier_value'],
        'query': ratings['query'],
        'ratings': ratings['ratings']
    })

    ratings_file.write(json.dumps(ratings_arr))
    ratings_file.close()

    return Response(status=status.HTTP_200_OK)


# added by genie
def get_sections(articles):
    result = []

    # sections = ArticleSection.objects.
    for a in articles:
        tmp = {
            'article_id': a.id,
            'sections': []
        } 
        try:
            for sec in ArticleSection.objects.filter(article=a):
                tmp['sections'].append({
                    'num': sec.num,
                    'title': sec.title,
                    'topics': get_sec_topics(sec)
                })
        except:
            print 'no sections for article %s' % a
            continue
        result.append(tmp)
    return result


def get_topics(articles, normalise=True):
    # return [] # XXX
    result = []

    for a in articles:
        tmp = {
            'article_id': a.id,
            'topic_dist': []
        }
        try:
            for tw in TopicWeight.objects.filter(article=a):
                tmp['topic_dist'].append({
                    'label': '\n'.join(tw.topic.label.split(',')),
                    'num': tw.topic.num,
                    'weight': float("{0:.2f}".format(tw.weight*100)),
                    'prop': tw.weight
                })
        except:
            print 'no topics for article %s' % a
            continue

        if normalise:
            weight_sum = sum([t['prop'] for t in tmp['topic_dist'] if t['prop'] > 0.05])
            for t in tmp['topic_dist']:
                t['prop'] /= (weight_sum / 100)
                # t['prop'] = float("{0:.2f}".format(t['weight']))
        else:
            for t in tmp['topic_dist']:
                t['prop'] *= 100
                # t['prop'] = float("{0:.2f}".format(t['weight']))
        result.append(tmp)
    return result


def get_sec_topics(sec, normalise=True):
    result = []
    try:
        for tw in TopicWeight.objects.filter(section=sec):
            result.append({
                'label': '\n'.join(tw.topic.label.split(',')),
                'num': tw.topic.num,
                'weight': float("{0:.1f}".format(tw.weight*100)),
                'prop': tw.weight
            })
    except:
        print 'no topics for section %s' % sec

    if normalise:
        weight_sum = sum([t['prop'] for t in result if t['prop'] > 0.05])
        for t in result:
            t['prop'] /= (weight_sum / 100)
            # t['weight'] = float("{0:.2f}".format(t['weight']))
    else:
        for t in result:
            t['prop'] *= 100
            # t['weight'] = float("{0:.2f}".format(t['weight']))

    return result


# def tw2pros(tw, normalise=True) :
# return tw


@api_view(['GET'])
def topics(request):
    # /topics?from=0&to=100&participant_id=1
    print json.dumps(request.GET, sort_keys=True, indent=4, separators=(',', ': '))

    try:
        from_article = int(request.GET['from'])
        to_article = int(request.GET['to'])
        normalise = int(request.GET.get('normalise', 1))
        participant_id = request.GET['participant_id']

        if not participant_id:
            participant_id = request.session.session_key

    except:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if to_article <= from_article:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=participant_id)

    except User.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    e = get_experiment(user)

    print "#iterations =", e.number_of_iterations

    if e.number_of_iterations == 0:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if e.number_of_iterations == 1:
        articles = get_articles("bm25", e, from_article, to_article - from_article)
        return Response(get_topics(articles, normalise))

    articles, keyword_stats, article_stats, stems = get_top_articles_linrel(e,
                                                                            from_article,
                                                                            to_article - from_article,
                                                                            e.exploration_rate)

    return Response(get_topics(articles, normalise))
