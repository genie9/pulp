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
    args = '<articles text mapping file>'
    help = 'loads articles text to into DB'

    def handle(self, *args, **options) :

#        dist_file = 'db_full.txt'

        article_count = Article.objects.count()
        if article_count == 0 :
            print >> stderr, "Error, article table must be built first!"
            exit(1)

        articles = Article.objects.all()

        expected_number_of_fields = 2

        print >> stderr, "reading %s ..." %  args[0]

        with open(args[0]) as f: 

            linenum = 0

            with transaction.atomic() :
                for line in f :
                    line = line.strip()

                    if not line or line.startswith('#') :
                        continue
                
                    data = line.split('\t')

                    if len(data) != expected_number_of_fields :
                        print >> stderr, "Error, line %d: expected %d fields, read %d fields" % \
                            (linenum, expected_number_of_fields, len(data))
                        continue

                    # a = articles[int(data[0])]

                    arx_num = data[0].split('/')[-1].split('.txt')[0]
#                    if 'cs' in arx_num :
#                        arx_num = arx_num.replace('cs', 'cs/')
#                        print arx_num
                    try :
                        a = articles.get(arxivid=arx_num)
#                        print a
                    except :
                        print >> stderr, "article %s doesn't exist, going to next one" % arx_num
                        continue
                    
                    linenum += 1

                    a.text = data[1]
                    a.save()

                    if (linenum % 1000) == 0 :
                        self.stderr.write("saved texts for %s articles" % linenum)
        f.closed

        print >> stderr, "Texts added to %d articles, supposed to be %d"%(linenum, article_count)

