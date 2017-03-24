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

#    COLORS = ["#7fdfc6","#ebaf95","#d0fab7","#99a7dd","#cf94a4","#ef8be3","#c58784","#b7c6b5","#e7f9b1","#c3aff1","#84c7b0","#f88bcb","#dffeca","#859dce","#7f8fdf","#eba78e","#f7eedc","#ef8e9e","#c6f6df","#ed86da","#ddd690","#a4d6cd","#af8ea4","#bfa8da","#f7daea","#b3dbc0","#9791d6","#afb8e0","#abebad","#d7b7eb","#ddf9b5","#87ada0","#cb88ed","#9fa9ad","#f6efed","#869588","#e0de94","#97d0a3","#c5acca","#bca4ad","#c6a79c","#c59df4","#afade3","#8ee2e9","#e6edb6","#b7df87","#b6f9a1","#f0c08f","#baba83","#e0aa9d","#f498c0","#8a9ca3","#89a4cc","#b0b790","#d88496","#e29ee4","#90c0ca","#f4be8d","#e2a1a6","#b3a3ce","#a5c49b","#97aac2","#aee1a8","#8a8fb8","#82bdb6","#fdcbae","#faccef","#98e2d7","#cae6af","#ba97a4","#c2a296","#eaf4b6","#f8f0c4","#f9b58d","#f1d8a4","#9a89ce","#a8ddb0","#ea85f6","#9f91e4","#9cb5b3","#d49ccb","#a1dbc2","#93e6c8","#edb0fa","#e5a198","#a4c5f2","#b4e2b5","#add8fc","#f8e3bf","#cef9aa","#e39dda","#e8ee88","#868eaa","#e7babb","#8c87f4","#8ca7c5","#9cedbb","#c7d9f2","#87cac3","#bdd7d5","#a1f7b2","#abedf5","#bd8a96","#d7a5de","#ec8cbd","#82d7c2","#bbb9c9","#beb1fb","#eba5a7","#85f097","#a8f59e","#86e9b9","#cfd4eb","#edeac9","#cf8898","#f199d0","#84e685","#a5e1fc","#c0dbf0","#81fdc6","#93b38d","#a5f9c0","#8ff78e","#dea9c7","#c0a8af","#86c7a9","#aac1e8","#ebfed5","#8996dd","#aeebd4","#cab5c5","#a197ac","#c8f0e8","#b4f6f9","#a1dcdf","#e4edd3","#b38296","#93f4d1","#c6d5bc","#de8fd5","#d7e285","#c6ddf7","#c08481","#c5aac5","#abf992","#9cddd7","#ead7be","#ef9c95","#c78695","#a7aec9","#dc96bc","#efc39f","#b0afbd","#c9808b","#b98fd2","#a48fc0","#8399ef","#958db1","#c4f283","#e4da9f","#cfbcda","#8ce9e4","#b59481","#9ff3ce","#a5f49c","#b4ecd8","#d789d6","#f4fcfc","#c39c9a","#97b6d4","#f1dceb","#fdd5b3","#c599c7","#cd8a9b","#90d693","#90fad8","#c4ccdb","#9ac287","#badedd","#8e95b0","#eb8cfc","#e4efce","#a39acc","#bae388","#a7a8b8","#e68bd0","#cd9080","#f6cefb","#d6ef8c","#faa8f0","#a0d9dc","#ecdbda","#ca998a","#a8a1d1","#d0f7a1","#e1e2c0","#efc4a2","#e3d98c","#ecb5b6","#adbdb8","#e2e9b8","#dcbb83","#c4d9f1","#c7cf91","#c5edb4","#c497ec","#c6efdf","#e188fe","#e9a9d3","#899891","#d6ecf0","#a7b89a","#a3a780","#ee84b8","#e6e2ef","#eab4b3","#8b98f5","#89f4f3","#95f6a2","#92fcd9","#f1da88","#d9bbc7","#b48da6","#bfbcb3","#87cebb","#ae85d7","#b2e18b","#9790f9","#a7af8f","#b7db96","#df9cbc","#ecc0b3","#a7e888","#f2fe99","#8b84d1","#a89dda","#ac81b5","#abfadb","#927fc5","#ddb786","#8896aa","#82d9a3","#dbdab4","#d2f58e","#d9edf4","#de88ef","#cd8d85","#94dfa9","#8196d2","#bc98ae"]
        

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

