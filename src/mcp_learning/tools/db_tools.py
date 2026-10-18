import os
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
import atexit

load_dotenv()

pool=ConnectionPool(
    kwargs={
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    },
    min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1")),
    max_size=int(os.getenv("DB_POOL_MAX_SIZE", "5")),
    timeout=int(os.getenv("DB_POOL_TIMEOUT", "10"))
)

atexit.register(pool.close)

def _query(sql,params=(),fetch="all"):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql,params)

            if fetch=="all":
                return cur.fetchall()
            elif fetch=="one":
                return cur.fetchone()
            return cur.rowcount

def _course(r):
    return dict(zip(["id","title","category","difficulty"],r))

def _lesson(r):
    return dict(zip(("id", "course_id", "title", "duration_minutes", "is_completed"), r))

def list_courses():
    """Return all courses ordered by course ID."""
    rows=_query("SELECT id, title, category, difficulty FROM courses ORDER BY id")
    return [_course(row) for row in rows]

DIFFICULTIES = {"Beginner", "Intermediate", "Advanced"}

def search_courses(search_item="", category="",difficulty=""):
    """Search courses by title, category, or difficulty."""
    if difficulty and difficulty not in DIFFICULTIES:
        raise ValueError(f"Invalid difficulty level: {difficulty}. Must be one of {DIFFICULTIES}")

    rows=_query(
        "SELECT id, title, category, difficulty FROM courses WHERE title ILIKE %s AND category ILIKE %s AND difficulty ILIKE %s ORDER BY id",
        (f"%{search_item}%", f"%{category}%", f"%{difficulty}%"))
    return [_course(row) for row in rows]

def get_course(course_id:int):
    """Return one course by ID, or an error when it does not exist."""
    row=_query("SELECT id, title, category, difficulty FROM courses WHERE id=%s", (course_id,), fetch="one")
    return _course(row) if row else {"error": "Course not found"}


def add_course(title: str, category: str, difficulty="Beginner"):
    """Create a course after validating its title, category, and difficulty."""
    title, category = title.strip(), category.strip()

    if not title or len(title) > 150:
        return {"error": "Title must contain 1-150 characters"}
    if not category or len(category) > 50:
        return {"error": "Category must contain 1-50 characters"}
    if difficulty not in DIFFICULTIES:
        return {"error": "Invalid difficulty"}

    return _course(_query(
        """INSERT INTO courses (title, category, difficulty)
           VALUES (%s, %s, %s)
           RETURNING id, title, category, difficulty""",
        (title, category, difficulty),
        "one",
    ))


def update_course(course_id: int, title=None, category=None, difficulty=None):
    """Update one or more fields of an existing course."""
    updates = {}

    if title is not None:
        title = title.strip()
        if not title or len(title) > 150:
            return {"error": "Title must contain 1-150 characters"}
        updates["title"] = title

    if category is not None:
        category = category.strip()
        if not category or len(category) > 50:
            return {"error": "Category must contain 1-50 characters"}
        updates["category"] = category

    if difficulty is not None:
        if difficulty not in DIFFICULTIES:
            return {"error": "Invalid difficulty"}
        updates["difficulty"] = difficulty

    if not updates:
        return {"error": "Provide at least one field to update"}

    clause = ", ".join(f"{col} = %s" for col in updates)
    row = _query(
        f"""UPDATE courses SET {clause} WHERE id = %s
            RETURNING id, title, category, difficulty""",
        (*updates.values(), course_id),
        "one",
    )
    return _course(row) if row else {"error": "Course not found"}


def delete_course(course_id: int, confirm=False):
    """Delete a course only when confirm is set to true."""
    if not confirm:
        return {"error": "Deletion cancelled; set confirm=true to proceed"}

    row = _query(
        "DELETE FROM courses WHERE id = %s RETURNING id, title",
        (course_id,),
        "one",
    )

    if not row:
        return {"error": "Course not found"}

    return {"deleted": True, "id": row[0], "title": row[1]}


def get_lessons(course_id: int):
    """Return all lessons for a course ordered by lesson ID."""
    rows = _query(
        """SELECT id, course_id, title, duration_minutes, is_completed
           FROM lessons
           WHERE course_id = %s
           ORDER BY id""",
        (course_id,),
    )
    return [_lesson(row) for row in rows]


def mark_lesson_completed(lesson_id: int, completed=True):
    """Mark a lesson as completed or incomplete."""
    row = _query(
        """UPDATE lessons SET is_completed = %s
           WHERE id = %s
           RETURNING id, title, is_completed""",
        (completed, lesson_id),
        "one",
    )

    if not row:
        return {"error": "Lesson not found"}

    return {"id": row[0], "title": row[1], "is_completed": row[2]}


def get_learning_progress():
    """Return lesson completion totals and remaining lessons per course."""
    rows = _query(
        """SELECT c.id, c.title, COUNT(l.id),
                  COUNT(l.id) FILTER (WHERE l.is_completed)
           FROM courses c
           LEFT JOIN lessons l ON l.course_id = c.id
           GROUP BY c.id, c.title
           ORDER BY c.id"""
    )

    return [
        {
            "course_id": r[0],
            "course_title": r[1],
            "total_lessons": r[2],
            "completed_lessons": r[3],
            "remaining_lessons": r[2] - r[3],
        }
        for r in rows
    ]
