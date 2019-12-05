# Project 1

Web Programming with Python and JavaScript

Application.py contains the main code for Project 1. It has routes for registering an account,
logging in and out, an index route where users can search for a book and a book page where
all submitted reviews are displayed and if not yet done, users can submit their own review.
Additionally, the book route displays an average user rating from Goodreads using the API Key.
Furthermore a API route is specified where users can retrieve data from this web app.

Helpers.py has the login_required defined as well as an error message function.

Layout.html provides the skeleton for the website's layout.
Index.html welcomes a user with his username, displays a search form to look up books via isbn,
book title, author or release year.
Book.html displays the book details, current reviews and if the user has not submitted a review yet,
a form with which the user can submit his own review. Goodread's average rating and review count is
also displayed.
Login.html, Register.html are for registering or logging in into the website.

All HTML files use the Bootstrap Library for styling the page, some minimal adjustments were made in styles.css

Import.py imports books into a postgreSQL Database which is hosted by Heroku.
Books.csv was provided by the CS50 staff and contains a list of books.

Used technologies, frameworks or languages:
Python (Flask)
HTML5
CSS
JSON 
