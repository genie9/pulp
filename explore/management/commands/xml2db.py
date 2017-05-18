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
from explore.models import Article
from sys import stderr
import datetime


a_id = ''
ids = []

class ArticleParser(xml.sax.ContentHandler) :
    def __init__(self) :
        self.content = None
        self.article = None
        self.count = 0
 
    def cleaned(self) :
        return self.content.replace('\n', ' ').strip()
        #return xml.sax.saxutils.escape(self.content.replace('\n', ' ').strip())

    def startElement(self, name, attrs) :
        self.content = ""

        if name == 'article' :
            self.article = Article()

    def characters(self, c) :
        self.content += c

    def endElement(self, name) :
        global ids, a_id 

        try :
            if name == 'article' : 
                if self.article :
                    if a_id in ids :
                        self.article.save()
                        self.article = None
                        self.count += 1
                    else : print '%s will not be recorded: not in ids list'%a_id
                    if (self.count % 1000) == 0 :
                        print >> stderr, "read in %d articles" % self.count

            elif name == 'title'    : self.article.title    = self.cleaned()
            elif name == 'author'   : self.article.author   = self.cleaned()
            elif name == 'abstract' : self.article.abstract = self.cleaned()
            elif name == 'venue'    : self.article.venue    = self.cleaned()
            elif name == 'url'      : self.article.url      = self.cleaned()
            elif name == 'id'       : 
                if 'cs' in self.content :
                    self.content = self.content.replace('cs/', 'cs')
                self.article.arxivid = self.cleaned()
                a_id = self.article.arxivid
            elif name == 'created'  : self.article.date     = datetime.date(*[ int(i) for i in self.cleaned().split('-')])
            else : pass

        except Exeption as ex:
            template = "An exception of type {0} occurred in article {1}. Arguments:\n{2!r}"
            message = template.format(type(ex).__name__, c, ex.args)
            print >> stderr, message
#        except TypeError :
#            print 'TypeError %s'%self.article.arxivid
#        except ValueError :
#            print 'ValueError %s'%self.article.arxivid

class Command(BaseCommand) :
    args = '<id file> <XML file> <XML file> ...'
    help = 'loads the articles from XML file into DB'

    def handle(self, *args, **options) :
        global ids 
        parser = xml.sax.make_parser()
        parser.setContentHandler(ArticleParser())

        initial_count = Article.objects.count()

        with open(args[0],'r') as f :
            ids = f.read().split('\n')
        f.closed

        for xmlfile in args[1:] :
            pre_count = Article.objects.count()

            try :
                with transaction.atomic() :
                    parser.parse(open(xmlfile))

            except IOError, ioe :
                raise CommandError(str(ioe))
            except xml.sax.SAXParseException, spe :
                raise CommandError(str(spe))
        
            post_count = Article.objects.count()
            self.stdout.write("added %d articles from %s" % (post_count - pre_count, xmlfile))

        self.stdout.write("\nDone! added %d articles total from %d file%s" % \
                (Article.objects.count() - initial_count, len(args), "" if len(args) == 1 else "s"))

