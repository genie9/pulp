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
from explore.models import Topic, Article, TopicWeight, ArticleSection
from sys import stderr


class Command(BaseCommand):
    args = '<topic file>'
    help = 'loads section topic weights of articles from mallet txt file to DB'

    def handle(self, *args, **options):

        NUM_TOPICS_TO_STORE = 10
        mallet_file = 'secs_100_props.txt'

        topic_count = Topic.objects.count()
        if topic_count == 0:
            print >> stderr, "Error, topic table must be built first!"
            exit(1)

        article_count = Article.objects.count()
        if article_count == 0:
            print >> stderr, "Error, article table must be built first!"
            exit(1)

        section_count = ArticleSection.objects.count()
        if section_count == 0:
            print >> stderr, "Error, section table must be built first!"
            exit(1)

        topics = Topic.objects.all()
        articles = Article.objects.all()
        sections = ArticleSection.objects.all()

        # updating TopicWeight table of DB with sections topic weights
        expected_number_of_fields = topic_count + 2
        print >> stderr, "reading %s ..." % mallet_file

        with open(mallet_file) as f:
            linenum = 0

            with transaction.atomic():
                for line in f:
                    linenum += 1

                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    data = line.split()

                    if len(data) != expected_number_of_fields:
                        print >> stderr, "Error, line %d: expected %d fields, read %d fields" % \
                                         (linenum, expected_number_of_fields, len(data))
                        continue

                    try :
                        arx_num, sec_num = data[1].split('/')[-1].split('.txt')[0].split('_')
                    except ValueError :
                        print >> stderr, "Error: wrong number of tokens, line %d tokens: %s" % (linenum, data[1])
                        continue

                    # arx_num = data[1].split('/')[-1].split('.txt')[0].split('_')[0]
                    # sec_num = data[1].split('/')[-1].split('.txt')[0].split('_')[1]

                    try:
                        s = sections.get(articles=articles.get(arxivid=arx_num), num=sec_num)
                        print s
                    except:
                        print 'Warning: article %s not in topic list, going to next one' % arx_num
                        continue

                    # finding best topics and their numbers, added by genie
                    dist = map(float, data[2::])
                    top_ind = sorted(range(len(dist)), key=lambda k: dist[k], reverse=True)[0:NUM_TOPICS_TO_STORE]

                    tw = TopicWeight()

                    for i in range(len(top_ind)):
                        tw.section = s
                        tw.topic = topics.get(num=top_ind[i])  # topics[top_ind[i]]
                        tw.weight = dist[top_ind[i]]  # float(data[i+1])

                        tw.save()

                    print top_ind

                    if (linenum % 1000) == 0:
                        self.stderr.write("saved topic weights for %s sections" % linenum)

        expected_weights = NUM_TOPICS_TO_STORE * article_count
        print >> stderr, "Warning: Wrote %d topic weight objects. I was expecting %d (%d articles x %d topics)." \
                         % (TopicWeight.objects.count(), expected_weights, article_count, NUM_TOPICS_TO_STORE)
