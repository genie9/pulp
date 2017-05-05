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
from explore.models import Topic
from sys import stderr

class Command(BaseCommand) :
    args = ['secs_100_keys.txt','topics_summary_nums.txt','colors.txt']
    help = 'loads topics from txt file into DB'
    COLORS = args[2]

    def handle(self, *args, **options) :

        NUM_KEYWORDS = 5
        
        colors = open(self.COLORS).read().split(',')
#        colors = COLORS
        print colors

        print len(colors)

        topics = Topic.objects
        if topics.count() != 0 :
            print >> stderr, "Deleting %d Topic objects" % topics.count()
            topics.all().delete()
            print >> stderr, "done!"

        with open(self.args[1]) as f :
            nums = f.read().split()
        f.closed
        # arxiv_cs_example/topic_top_keywords
        with open(self.args[0]) as f :
            linenum = 0

            for line in f :
                linenum += 1

                line = line.strip()
                if not line :
                    continue

                try :
                    num,something,keywords = line.split('\t')

                except ValueError :
                    print >> stderr, "Error: too many tokens, line %d" % linenum
                    continue

                keywords = keywords.split()

                with transaction.atomic() :
                    t = Topic()
                    t.label = ','.join(keywords[:NUM_KEYWORDS])
                    # added by genie
                    t.num = num
                    t.color = colors[nums.index(num)]
                    t.save()

                    #for k in keywords :
                    #    kw = TopicKeyword()
                    #    kw.topic = t
                    #    kw.keyword = k
                    #    kw.save()

                #print >> stderr, "saved topic %s" % name

        print >> stderr, "added %d topics" % (Topic.objects.count())

