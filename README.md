# CINEMATCH Backend

## Table of Contents
- [Introduction](#introduction)
- [Setup Instructions](#setup-instructions)
- [Backend Architecture Overview](#backend-architecture-overview)
- [High Level Workflow Diagram for Session_routes.py](#high-level-workflow-diagram-for-session_routespy)
- [Database Tables for Session Management](#database-tables-for-session-management)
- [Potential Modification of the Database](#potential-modification-of-the-database)
- [Updates](#updates)
- [Contribution Guidelines](#contribution-guidelines)
- [License](#license)
- [Contact](#contact)

## Introduction

This project, developed for CS506, is a group movie selection platform called **Cinematch**. It allows friends to **start a session or join a group** and collaboratively choose a movie through a Tinder-like swiping and voting system. The app aims to make movie picking fun, interactive, and democratic among friends.

Movie data is retrieved live from the TMDb API, while session-related information (such as participant lists and voting progress) is managed through a structured local database (`movies_v2.db`). For frontend testing purposes, a compiled HTML file (`complete_version_html_testing.html`) and the updated database are available in the project’s Google Drive.

Unit tests for API endpoints can be run using **pytest** directly from the terminal. Although there may be minor adjustments at the end that cause some test cases to fail, most APIs are internal and protected from invalid user inputs, ensuring stable backend behavior in typical usage scenarios.


## Version Control
- Python Version: Conda 3.10.0
- Install dependencies using:
  ```sh
  pip install -r requirements.txt
  ```

## Setup Instructions
1. Clone the repository:
   ```sh
   git clone https://github.com/Steal-Your-Data/backend.git
   ```
2. Create and activate a Conda environment (optional but recommended):
   ```sh
   conda create --name movie-swipe-app python=3.10.0
   conda activate movie-swipe-app
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Run the application:
   ```sh
   python app.py
   ```

## Backend Architecture Overview

The backend of **Cinematch** is built with **Flask** and organized into modular blueprints for scalability and clarity. We use **Flask-SQLAlchemy** to manage session-related data and **Flask-SocketIO** to enable real-time communication during movie selection sessions. The system is divided into key modules: `session_routes.py` manages user sessions (starting, joining, voting), `movie_routes.py` handles movie search and filtering (primarily via live TMDb API calls), `socket_events.py` handles real-time room-based updates, and `Utils.py` provides helper functions for external API queries. While most movie information is fetched directly from TMDb, session-related data — such as session details, participants, and temporary movie pockets for voting — continues to be stored and retrieved from the local SQLite database (`movies_v2.db`).

Our backend is designed for an interactive, scalable, and fault-tolerant user experience. APIs are paginated for efficient data handling, Socket.IO ensures synchronized updates across participants, and the database maintains essential session state information. This architecture offers a dynamic, real-time movie-matching experience while balancing external API responsiveness with local session persistence.

## High Level Workflow Diagram for Session_routes.py
![Alt text](WorkFlow_Chart.jpeg)

### How Session Management Works

The above diagram illustrates the full lifecycle of a movie selection session in **Cinematch**, as managed by `session_routes.py` and `socket_events.py`.

1. **Session Initialization**: A host begins by starting a session using `/start`, while guests join using `/join`. All participants are then added to a Socket.IO room for real-time communication (`join_session_room` event).

2. **Session Start**: When the host begins the session with `/begin`, a Socket.IO broadcast notifies all users that movie selection can begin.

3. **Movie Selection Phase**: All users can add movies to the session using `/add_movie`. Once a user finishes their selection, they call `/finish_selection`. When all participants finish, a broadcast notifies everyone that voting is next.

4. **Swiping & Voting Phase**: Users enter the Tinder-like swiping interface. Votes are submitted via `/vote`, and each participant calls `/finish_voting` when done. When everyone finishes voting, the backend tallies the result.

5. **Final Decision Broadcast**: The winning movie is computed and retrieved through `/final_movie`, and a broadcast shares the decision with the group.

This real-time workflow combines RESTful APIs with WebSocket events to ensure a smooth, interactive, and collaborative movie-picking experience.



## Database Tables for Session Management

The `movies_v2.db` database still plays an important role in **session management**. The following tables are actively used by the backend:

- **Session**: Stores information about each movie selection session, including session ID and host user.
- **SessionParticipant**: Tracks participants who have joined a session, along with their selection and voting status.
- **MoviePocket**: Temporarily stores selected movies for a session along with their vote counts, allowing collaborative voting.

These tables are primarily accessed and modified through APIs defined in `session_routes.py`. They ensure that session states, participant data, and voting results are consistently managed across user interactions.

---

### Table Structures
#### 1. Session Table (`session`)

| Column Name | Type    | Description                                         |
|-------------|---------|-----------------------------------------------------|
| id          | TEXT    | Primary Key (Random 6-digit session ID as string)    |
| host_name   | TEXT    | Host username or user ID                            |
| status      | TEXT    | Status of the session (e.g., pending, active, completed) |

---

#### 2. SessionParticipant Table (`session_participant`)

| Column Name         | Type    | Description                                   |
|---------------------|---------|-----------------------------------------------|
| id                  | INTEGER | Primary Key (Auto-increment)                  |
| session_id          | TEXT    | Foreign Key linked to `session.id`            |
| name                | TEXT    | Name of the participant                      |
| done_selecting      | BOOLEAN | Whether the participant has finished selecting movies |
| done_voting         | BOOLEAN | Whether the participant has finished voting  |

---

#### 3. MoviePocket Table (`movie_pocket`)

| Column Name       | Type    | Description                                               |
|-------------------|---------|-----------------------------------------------------------|
| id                | INTEGER | Primary Key (Auto-increment)                              |
| session_id        | TEXT    | Foreign Key linked to `session.id`                        |
| movie_id          | INTEGER | Foreign Key linked to `movies.id` (nullable if external movie) |
| votes             | INTEGER | Number of votes the movie has received in this session     |

---

## Potential Modification of the Database
---

### 1. Update the `MoviePocket` Model in `models.py`

Since we need to implement add functions when we encounter a case where there is no such a movies in the database. Thus there will be slightly modification on the code.

Firstly, Modify the `MoviePocket` class in your Flask application to include the new columns:

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class MoviePocket(db.Model):
    __tablename__ = 'movie_pocket'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Text, db.ForeignKey('session.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'))
    votes = db.Column(db.Integer, default=0)

    # New columns (nullable)
    title = db.Column(db.String(100))
    genres = db.Column(db.String(100))
    original_language = db.Column(db.String(10))
    overview = db.Column(db.Text)
    popularity = db.Column(db.Float)
    release_date = db.Column(db.Date)
    poster_path = db.Column(db.String(200))
```

In the database (`movies_v2.db`), also please change the table

```sqlite3
-- Drop the existing table if it exists
DROP TABLE IF EXISTS movie_pocket;

-- Create the new table with updated schema
CREATE TABLE movie_pocket (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session(id),
    movie_id INTEGER REFERENCES movies(id),
    votes INTEGER DEFAULT 0,
    title TEXT,
    genres TEXT,
    original_language TEXT,
    overview TEXT,
    popularity REAL,
    release_date DATE,
    poster_path TEXT
);
```

And also You might change the add_movies API in session_routes.py accordingly

## Updates

## Updates 3/2/2025

Fixing/Solving some potential inconvenience for the front-end guys. In (`socket_events.py`). Previously, the function called (`handle_join_session_room()`) only emit messages about which user joining the session, but not a whole list of people in this session. This will cause inconvenience when We update the joining guest list in the frontend. Since they need to call twice firstly when they join they will call (`list_participants()`) in session_routes.py and then they need to listen to SocketIO broadcast to add other person who are newly joining the session one by one, which might be inconvenient to impelement in the front end. Thus the newly (`socket_events.py`) is a compiled version of it. In the frontend, only need to listen to socket events **join_session_room**, then you will get the updated session participants list in the session. Though the cost is a bit high in the frontend, but considering for one session, probably there will only be 8 - 9 people at maximum, it is not a big deal to update the list 8 to 9 times.

Below are the new logs, once we hit the join_room button under Socket.IO Actions in .html file called (`complete_version_html_testing.html`)

![Alt text](new_output_for_joinroom.jpeg)

## Updates 3/6/2025

Updated the model.py to have string id instead and ensured randomly generating a new session id so duplicate error does not occur anymore


## Updates 3/28/2025

Updated the **folder (`test/`)** for doing basic unit testing for each API, bascially for **corner case** testing. This test aims to build a very decent fault-tolerance system. There are total of 50 test cases for testing the APIs' fault-tolerance ability. Based on the test cases, Modifying the APIs a little bit handling invalid input. But still using **(`complete_version_html_testing.html`)** for testing if each APIs is working good after modifying the current APIs. As a result, current APIs in this branch pass both **folder (`test/`)** and **(`complete_version_html_testing.html`)**. To simply run the unit test just in the backend folder and open terminal run **(`pytest`)** 

## Updates 4/2/2025


Finished updating the movie_routes.py below are the new routes I added to the repo:


(`/search_API`):Searches movies via TMDb API.
(`/get_movie_info_by_id_API`): Fetches single movie info by ID via TMDb API.
(`/get_movie_info_by_ids_API`): Fetches multiple movie infos by ID list via TMDb API.
(`/get_all_movies_V2`): Returns 10 movies per page from local DB.
(`/sort_movies_V2`): Returns sorted movies (by title, popularity, release_date) with pagination(pages).
(`/filter_movies_V2`): Returns filtered movies (by genres, language, release_year) with pagination(pages).

the routes from **bullet 4** to **bullet 6** are confirmed with Rushil yesterday night to add that to the movie_routes.py. Since we both think it is a little bit weird if we retrieve all the movies at once to the frontend, we stick to every time we only retrieves 10 movies, once user scroll down it will load more movies by calling this function with +1 pages.  

from **bullet 1** to **bullet 3** are the API we have plan to use in the final version of Cinematch.  after yesterday's discussion with Rushil, which directly call from the TMBD API to get the movie info. with the same I/O as the corresponding API Before.  


## Updates 4/3/2025

### Only in Theater Filtering in `filter_movies_V2`

We have enhanced the `/movies/filter_movies_V2` route by adding the `only_in_theater` option. With this update, the API can now return movies that are currently playing in US cinemas.

#### Overview

- **Route:** `/movies/filter_movies_V2`
- **Feature:** When the query parameter `only_in_theater=yes` is provided, the route will fetch movies that are now playing in theaters from TMDb.
- **Filters:** You can still filter by `genres`, `language`, and `release_year`.
- **Pagination:** The results are paginated. For example:
  - `page=1` returns the first 12 matching movies,
  - `page=2` returns movies 13–24,
  - and so on.

#### Example API Call

```http
GET http://127.0.0.1:5000/movies/filter_movies_V2?genres=Action&genres=Drama&page=9&language=en&only_in_theater=yes
```


## Updates 4/11/2025

As discuss with Integration team members, We have a agreement on building a get_all_movies function by calling the API instead of 
Local data base, now the function is complete and can be found in movies_routes.py the function name is called (`@movie_bp.route('/get_all_movies_API', methods=['GET'])
def get_all_movies_API():`) same I/O as get_all_movies_V2


## Contribution Guidelines
- Follow the Git branching workflow (`feature-branch`, `dev`, `main`).
- Use descriptive commit messages.
- Create pull requests for merging new features.

## License
This project is for educational purposes under CS506 and is not intended for commercial use.

## Contact
For any issues or contributions, please contact the development team via the repository's issue tracker.

