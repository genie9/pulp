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
from explore.models import Article, ArticleSection
from sys import stderr


class Command(BaseCommand):
    args = '<section title file>'
    help = 'loads sections of articles from txt file to DB'

    def handle(self, *args, **options):
#        title_file = 'section_titles.txt'

        article_count = Article.objects.count()
        if article_count == 0:
            print >> stderr, "Error, article table must be built first!"
            exit(1)

        section_count = ArticleSection.objects.count()
        if section_count != 0:
            print >> stderr, "Deleting %d ArticleSection objects" % section_count
            ArticleSection.objects.all().delete()
            print >> stderr, "done!"

        articles = Article.objects.all()

        # filling ArticleSection table of DB
        print >> stderr, "reading %s ..." % args[0]

        with open(args[0]) as f:
            linenum = 0
            saved = 0
            not_count = 0

            with transaction.atomic():
                for line in f:
                    linenum += 1

                    line = line.strip()
                    if not line or line.startswith('#'):
                        not_count += 1
                        continue

                    try:
                        article, title = line.split(',', 1)
                    except ValueError:
                        print >> stderr, "Error: wrong number of tokens in read line, line %d tokens. %s" \
                                         % (linenum, line)                        

                    if title == 'abstr' :
                        title = 'Abstract'

                    try:
                        arx_num, sec_num = article.split('_')
                    except ValueError:
                        print >> stderr, "Error: wrong number of tokens in section number, line %d tokens: %s" \
                                         % (linenum, article)
                        continue
                    
#                    check = False
#                    if 'cs' in arx_num :
#                        arx_num = arx_num.replace('cs', 'cs/' )
#                        print arx_num
#                        check = True

                    try:
                        a = articles.get(arxivid=arx_num)
#                        if check :
#                            print '%s article %s section %s' % (arx_num, a, title)
                    except:
                        print >> stderr, 'article %s from sections list not found in article table, going to next one' % arx_num
                        continue

                    section = ArticleSection()
                    try:
                        section.num = int(sec_num)
                        section.article = a
                        section.title = title

                        section.save()
                    except Exeption as ex:
                        template = "An exception of type {0} occurred in article {1} section {2}. Arguments:\n{3!r}"
                        message = template.format(type(ex).__name__, arx_num, sec_num, ex.args)
                        print >> stderr, message

                    if sec_num == '0':
                        saved += 1
                    if (saved % 100) == 0:
                        self.stderr.write("saved %d sections for %d articles" % (linenum, saved))
            f.closed

        section_count = ArticleSection.objects.count()
        if section_count != (linenum - not_count):
            print >> stderr, "Warning: Different number of sections between file and DB! Read lines %d, DB entries %d" \
                  % (linenum - not_count, section_count)
