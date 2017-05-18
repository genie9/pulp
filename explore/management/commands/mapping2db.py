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

import xml.sax 
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from explore.models import Topic, Article, TopicWeight
from sys import stderr, exit


class Command(BaseCommand) :
    args = '<topic mapping file>'
    help = 'loads document to topic mapping file into DB'

    def handle(self, *args, **options) :

        NUM_TOPICS_TO_STORE = 10
#        dist_file = 'full_100_inf_props_100.txt'
        bad_topics = [4, 12, 18, 22, 24, 25, 32, 33, 38, 43, 47, 48, 50, 57, 61, 63, 65, 69, 77, 78, 82, 83, 86, 88, 89, 94, 97, 99]
#[10, 16, 17, 22, 23, 24, 25, 26, 32, 34, 35, 37, 40, 44, 47, 48, 54, 55, 56, 57, 62, 63, 66, 68, 72, 76, 83, 84, 85, 93, 94, 96, 97]

        topic_count = Topic.objects.count()
        if topic_count == 0 :
            print >> stderr, "Error, topic table must be built first!"
            exit(1)

        article_count = Article.objects.count()
        if article_count == 0 :
            print >> stderr, "Error, article table must be built first!"
            exit(1)

        if TopicWeight.objects.count() != 0 :
            print >> stderr, "Deleting %d TopicWeight objects" % TopicWeight.objects.count()
            TopicWeight.objects.all().delete()
            print >> stderr, "done!"

        topics = Topic.objects.all()
        articles = Article.objects.all()

        expected_number_of_fields = topic_count + 2  # (topic_count * 2) + 2

        print >> stderr, "reading %s ..." %  args[0]

        # arxiv_cs_example/doc-topics.txt
        with open(args[0]) as f:

            linenum = 0

            with transaction.atomic() :
                for line in f :
                    linenum += 1

                    line = line.strip()
                    if not line or line.startswith('#') :
                        continue
                
                    data = line.split()

                    if len(data) != expected_number_of_fields :
                        print >> stderr, "Error, line %d: expected %d fields, read %d fields" % \
                            (linenum, expected_number_of_fields, len(data))
                        continue

                    # a = articles[int(data[0])]

                    arx_num = data[1].split('/')[-1].split('.txt')[0]
#                    if 'cs' in arx_num :
#                        arx_num = arx_num.replace('cs', 'cs/')
#                        print arx_num
                    try :
                        a = articles.get(arxivid=arx_num)
#                        print a
                    except :
                        print >> stderr, "article %s doesn't exist, going to next one" % arx_num
                        continue

                    # finding best topics and their numbers, added by genie
                    dist = map(float, data[2::])
                    top_ind = [i for i in sorted(range(len(dist)), key=lambda k: dist[k], reverse=True) if i not in bad_topics][0:NUM_TOPICS_TO_STORE]
#                    top_ind = [i for i in sorted(range(len(dist)), key=lambda k: dist[k], reverse=True)][0:NUM_TOPICS_TO_STORE]

#                    print top_ind

                    # with transaction.atomic() :
                    for i in range(len(top_ind)) :  # 2 + (2 * NUM_TOPICS_TO_STORE), 2) : #range(2, len(data), 2) :

                        tw = TopicWeight()
                        
                        try:
                            tw.article  = a
                            tw.topic    = topics.get(num=top_ind[i])  # topics[top_ind[i]]
                            tw.weight   = dist[top_ind[i]]  # float(data[i+1])

                            tw.save()
                        except Exeption as ex:
                            template = "An exception of type {0} occurred in article {1}. Arguments:\n{3!r}"
                            message = template.format(type(ex).__name__, arx_num, ex.args)
                            print >> stderr, message

                    if (linenum % 1000) == 0 :
                        self.stderr.write("saved topic weights for %s articles" % linenum)
            f.closed

        expected_weights = NUM_TOPICS_TO_STORE * article_count
        print >> stderr, "Wrote %d topic weight objects. I was expecting %d (%d articles x %d topics)" \
                % (TopicWeight.objects.count(), expected_weights, article_count, NUM_TOPICS_TO_STORE)

