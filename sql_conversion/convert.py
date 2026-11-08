import sqlite3
import re
import sys
import traceback


def clean_line_syntax(line):
    """Strips out MySQL character sets, collations, and fixes types for SQLite compatibility."""
    # Remove MySQL specific column keys/indexes declarations
    if re.search(r'^\s*(UNIQUE\s+)?KEY\s+["`\w]', line, re.IGNORECASE):
        return ""
    if re.search(r'^\s*CONSTRAINT\s+["`\w]', line, re.IGNORECASE):
        return ""

    line = line.replace("`", '"')

    # Strip MySQL specific column collations: CHARACTER SET ... COLLATE ...
    line = re.sub(r"CHARACTER\s+SET\s+\w+", "", line, flags=re.IGNORECASE)
    line = re.sub(r"COLLATE\s+\w+", "", line, flags=re.IGNORECASE)

    # Convert auto-increment configurations to standard SQLite syntax
    line = re.sub(
        r"int\(.*\)\s+NOT\s+NULL\s+AUTO_INCREMENT",
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(
        r"int\(.*\)\s+AUTO_INCREMENT",
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(
        r"AUTO_INCREMENT", "PRIMARY KEY AUTOINCREMENT", line, flags=re.IGNORECASE
    )

    return line


def log_debug_error(error_type, error_msg, line_num, statement, original_line=None):
    """Formats a diagnostic report for any remaining syntax exceptions."""
    print("\n" + "=" * 80)
    print(f"❌ DATABASE MIGRATION EXCEPTION: {error_type}")
    print(f"   Error Message: {error_msg}")
    print(f"   Approximate File Line: {line_num}")
    print("=" * 80)

    if original_line:
        print(f"Raw Input Stream snippet:\n   {original_line.strip()[:120]}")
        print("-" * 80)

    clean_stmt = statement.strip()
    if len(clean_stmt) > 300:
        print(
            f"SQL Execution Block Context:\n   {clean_stmt[:180]} ...\n   ... {clean_stmt[-120:]}"
        )
    else:
        print(f"SQL Execution Block Context:\n   {clean_stmt}")
    print("=" * 80 + "\n")


def convert_sql_to_sqlite(sql_filepath, sqlite_filepath):
    print(
        f"Initialising multi-line streaming engine...\nSource: {sql_filepath}\nTarget: {sqlite_filepath}\n"
    )

    conn = sqlite3.connect(sqlite_filepath)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    in_create_table = False
    in_insert = False

    table_buffer = []
    insert_buffer = []

    success_count = 0
    fail_count = 0
    line_counter = 0

    try:
        with open(
            sql_filepath, "r", encoding="utf-8-sig", errors="surrogateescape"
        ) as f:
            for line in f:
                line_counter += 1
                line_strip = line.strip()

                # Skip comments and empty spaces
                if (
                    not line_strip
                    or line_strip.startswith("--")
                    or line_strip.startswith("#")
                    or line_strip.startswith("/*!")
                ):
                    continue

                if any(
                    line_strip.upper().startswith(x)
                    for x in ["SET ", "LOCK ", "UNLOCK ", "CREATE DATABASE", "USE "]
                ):
                    continue

                # --- STATE CONTROLLER: SCHEMA DEFINITIONS ---
                if line_strip.upper().startswith("CREATE TABLE"):
                    in_create_table = True
                    # Dynamically prepend IF NOT EXISTS to prevent duplicate structural crashes
                    mod_line = re.sub(
                        r"CREATE\s+TABLE",
                        "CREATE TABLE IF NOT EXISTS",
                        line,
                        flags=re.IGNORECASE,
                    )
                    table_buffer = [clean_line_syntax(mod_line)]
                    continue

                if in_create_table:
                    cleaned = clean_line_syntax(line)
                    if cleaned:
                        table_buffer.append(cleaned)
                    if line_strip.endswith(";"):
                        in_create_table = False
                        stmt = "".join(table_buffer)
                        stmt = re.sub(
                            r"\)\s*ENGINE\s*=\s*\w+.*$",
                            ")",
                            stmt,
                            flags=re.IGNORECASE | re.MULTILINE,
                        )
                        if not stmt.strip().endswith(";"):
                            stmt = stmt.strip() + ";"
                        try:
                            cursor.execute(stmt)
                            success_count += 1
                        except sqlite3.Error as e:
                            fail_count += 1
                            log_debug_error(
                                "Schema Definition Failure", e, line_counter, stmt
                            )
                    continue

                # --- STATE CONTROLLER: MULTI-LINE ROW INSERTIONS ---
                if line_strip.upper().startswith("INSERT INTO") or in_insert:
                    in_insert = True

                    # Sanitize formatting syntax instantly
                    processed_line = line.replace("`", '"')
                    processed_line = processed_line.replace(r"\'", "''")
                    processed_line = processed_line.replace(r"\"", '""')
                    insert_buffer.append(processed_line)

                    # Check if the block has reached its closing statement delimiter
                    if line_strip.endswith(";"):
                        in_insert = False
                        full_insert_stmt = "".join(insert_buffer)
                        insert_buffer = []

                        try:
                            cursor.execute(full_insert_stmt)
                            success_count += 1
                        except sqlite3.Error as e:
                            fail_count += 1
                            log_debug_error(
                                "Data Row Insertion Failure",
                                e,
                                line_counter,
                                full_insert_stmt,
                                original_line=line,
                            )
                    continue

    except Exception as general_err:
        print(f"\n💥 CRITICAL FILE READ FAILURE on line {line_counter}!")
        traceback.print_exc()
        conn.rollback()
        conn.close()
        sys.exit(1)

    print("Finalizing database write operations...")
    conn.commit()
    conn.close()
    print(
        f"\n🎉 Process Finished! Successfully parsed {success_count} structural groups. {fail_count} blocks failed."
    )

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert.py <input_dump.sql> <output_database.db>")
    else:
        # Index [1] is the input file, Index [2] is the output file
        convert_sql_to_sqlite(sys.argv[1], sys.argv[2])
