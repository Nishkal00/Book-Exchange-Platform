"""Locust load test scenario for NF-001 / TC-PERF-01.

Execution target:
- Endpoint: /api/v1/listings
- 50 concurrent users
- 10 users/second ramp-up rate
- 1-minute test duration
- p90 latency threshold: <= 2.0 seconds
- Target dataset: 10,000 listings across ~2,000 books and 20 users
"""

import random

try:
    from locust import HttpUser, between, task
except ImportError:
    # Locust is an optional benchmark runtime dependency
    HttpUser = object  # type: ignore[assignment, misc]

    def task(weight: int = 1):  # type: ignore[misc]
        def decorator(func):
            return func

        return decorator

    def between(a: float, b: float):  # type: ignore[misc]
        return lambda: a


TITLE_KEYWORDS = [
    "Algorithms",
    "Systems",
    "Networks",
    "Database",
    "Design",
    "Architecture",
    "Software",
    "Intelligence",
    "Learning",
    "Security",
    "Compiler",
    "Distributed",
    "Theory",
    "Engineering",
    "Science",
]

AUTHORS = [
    "Cormen",
    "Tanenbaum",
    "Silberschatz",
    "Martin",
    "Knuth",
    "Russell",
    "Norvig",
    "Gamma",
    "Fowler",
    "Hennessy",
    "Patterson",
    "Elmasri",
    "Navathe",
    "Aho",
    "Ullman",
]

LOCATIONS = [
    "Main Library",
    "Engineering Block",
    "Campus Center",
    "Science Library",
    "Hostel 1",
    "Hostel 2",
    "Hostel 3",
    "Hostel 4",
    "North Campus Study Room",
    "South Campus Student Hub",
]


class ListingSearchUser(HttpUser):
    """Simulated campus user searching listings under load."""

    wait_time = between(0.1, 0.5)

    @task(30)
    def search_by_title(self) -> None:
        """Search listings by title keyword (q)."""
        kw = random.choice(TITLE_KEYWORDS)
        with self.client.get(
            f"/api/v1/listings?q={kw}",
            name="/api/v1/listings?q=[title]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "items" in data and "total" in data:
                    response.success()
                else:
                    response.failure("Malformed response envelope")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(20)
    def search_by_author(self) -> None:
        """Search listings by author name (q)."""
        author = random.choice(AUTHORS)
        with self.client.get(
            f"/api/v1/listings?q={author}",
            name="/api/v1/listings?q=[author]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(15)
    def search_by_isbn(self) -> None:
        """Search listings by exact 13-digit ISBN."""
        idx = random.randint(1, 2000)
        isbn = f"978{idx:010d}"
        with self.client.get(
            f"/api/v1/listings?isbn={isbn}",
            name="/api/v1/listings?isbn=[isbn]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(15)
    def search_by_location(self) -> None:
        """Filter listings by location."""
        loc = random.choice(LOCATIONS)
        with self.client.get(
            f"/api/v1/listings?location={loc}",
            name="/api/v1/listings?location=[loc]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(10)
    def search_combined_filter(self) -> None:
        """Search using combined q and location filters."""
        kw = random.choice(TITLE_KEYWORDS[:5])
        loc = random.choice(LOCATIONS[:5])
        with self.client.get(
            f"/api/v1/listings?q={kw}&location={loc}",
            name="/api/v1/listings?q=[title]&location=[loc]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(8)
    def browse_pagination(self) -> None:
        """Browse paginated slices."""
        page = random.randint(1, 5)
        size = random.choice([10, 20, 50])
        with self.client.get(
            f"/api/v1/listings?page={page}&size={size}",
            name="/api/v1/listings?page=[p]&size=[s]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def default_search(self) -> None:
        """Fetch default first page of available listings."""
        with self.client.get(
            "/api/v1/listings",
            name="/api/v1/listings",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
