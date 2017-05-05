#!/bin/bash


rm db.sqlite3
python manage.py syncdb > write_db.log 2>&1
python manage.py xml2db ARXIV-MALLET_pretty.xml > write_db.log 2>&1
python manage.py text2article > write_db.log 2>&1
python manage.py okapibm25 > write_db.log 2>&1
python manage.py sections2db > write_db.log 2>&1
python manage.py topics2db > write_db.log 2>&1
python manage.py mapping2db > write_db.log 2>&1
python manage.py sec_mapping2db > write_db.log 2>&1
