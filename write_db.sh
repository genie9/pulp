#!/bin/bash

today=$(date +"%d%m%y")
write=write_db_${today}.log

rm db.sqlite3
python manage.py syncdb > $write 2>&1
python manage.py xml2db ARXIV_310316.xml >> $write 2>&1
python manage.py text2article db_full.txt >> $write 2>&1
python manage.py okapibm25 >> $write 2>&1
python manage.py sections2db section_titles.txt >> $write 2>&1 
python manage.py topics2db secs_nonstem_100_keys_uniq.txt topics_summary_nums.txt colors.txt >> $write 2>&1
python manage.py mapping2db full_nonstem_100_inf_props.txt >> $write 2>&1
python manage.py sec_mapping2db secs_nonstem_100_props.txt >> $write 2>&1
