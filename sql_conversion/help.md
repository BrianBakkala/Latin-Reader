### convert SQL=>SQLite from file

 - Download sqlite-tools-win-x64-**xxxx**.zip [https://www.sqlite.org/download.html]()

 - Put sqlite3.exe in this dir
 - Put SQL file in this dir (named db.sql)

 - Then run (from root):

```
python sql_conversion\convert.py sql_conversion\db.sql data.db
```