#!/bin/bash

today=$(date+%d%m%y)
log=write_db_${today}.log

rm db.sqlite3
python manage.py syncdb > write 2>&1
python manage.py xml2db ARXIV_310316.xml > write 2>&1
python manage.py text2article > write 2>&1
python manage.py okapibm25 > write 2>&1
python manage.py sections2db > write 2>&1
python manage.py topics2db > write 2>&1
python manage.py mapping2db > write 2>&1
python manage.py sec_mapping2db > write 2>&1
