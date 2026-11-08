import express from 'express';
import Database from 'better-sqlite3';
import path from 'path';

const app = express();
const port = process.env.PORT || 3000;

app.set('view engine', 'ejs');
app.use(express.urlencoded({ extended: true }));

//////
// db
//
const dbPath = path.resolve('db/main.db');
const db = new Database(dbPath);
console.log(`📍 Database file targeted at: ${dbPath}`);


// static files
app.use(express.static('public'));


//main route
app.get('/', (req, res, next) =>
{
  try
  {
    const users = db.prepare('SELECT * FROM text_vergil_aeneid').all();
    res.render('users', { users });
  } catch (err)
  {
    next(err);
  }
});

//view route
app.get('/view', (req, res, next) =>
{
  try
  {
    const text = db.prepare('SELECT * FROM text_vergil_aeneid').all();
    res.render('text', { text });
  } catch (err)
  {
    next(err);
  }
});



//error
app.use((err, req, res, next) =>
{
  console.error('❌ Express Application Error:', err.stack);
  res.status(500).send(`<h1>Internal Server Error</h1><pre>${err.message}</pre><a href="/">Go Back to Dashboard</a>`);
});

app.listen(port, () =>
{
  console.log(`🌐 Server running on: http://localhost:${port}`);
});
