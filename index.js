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
		 res.send(` Go to <a href="/view/v-aeneid/1/1/10">View</a></a>`);
	} catch (err)
	{
		next(err);
	}
});

//view route
app.get('/view/:textSlug/:book{/:startChapter/:endChapter}/:startLine/:endLine', (req, res, next) =>
{
	try
	{
		const table = db.prepare('SELECT table_suffix FROM texts WHERE slug = ?').get(req.params.textSlug);
		const text = db.prepare(`SELECT t.*,
			 p.definition as primary_definition, s.definition as secondary_definition ,
			 p.entry as primary_entry, s.entry as secondary_entry
			 
			 FROM text_${table.table_suffix}  t
				LEFT JOIN reference_dictionary p ON (t.definition_id = p.id)
				LEFT JOIN reference_dictionary s ON (t.secondary_definition_id = s.id)
			WHERE book_number = ?  AND line_number >= ? AND line_number <= ?`).all(
			req.params.book ? req.params.book : null,
			req.params.startLine ? req.params.startLine : null,
			req.params.endLine ? req.params.endLine : null
		);

		const wordIds = text.map(x => x.id).filter(x => x !== null);

		const commentary = db.prepare(`
				SELECT *
				FROM commentary_${table.table_suffix}
				WHERE EXISTS (
					SELECT 1
					FROM json_each(commentary_${table.table_suffix}.word_ids)
					WHERE json_each.value IN (${wordIds.map(() => '?').join(',')})
				)
    		`)
			.all(...wordIds)
			.map(x =>
			{
				return {
					note_id: x.note_id,
					commentary_text: x.commentary_text,
					text_id: x.text_id,
					words: Object.values(JSON.parse(x.word_ids))
						.map(w => Object.values(text).find(t => t.id === w))
						.filter(w => w !== undefined)
						.sort((a, b) => a.order_of_text - b.order_of_text)
					,
					lines: x.line_ids ? (JSON.parse(x.line_ids)[0] === "" ? null : JSON.parse(x.line_ids)) : null
				};
			});

		res.render('text', {
			text,
			commentary: Object.values(commentary),
			book: req.params.book ? req.params.book : null,
			startLine: req.params.startLine ? req.params.startLine : null,
			startChapter: req.params.startChapter ? req.params.startChapter : null,
			endChapter: req.params.endChapter ? req.params.endChapter : null,
			endLine: req.params.endLine ? req.params.endLine : null
		});
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
