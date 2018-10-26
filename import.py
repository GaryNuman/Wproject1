import csv
# os odule provides a way of using operating system dependent functionality
import os

# the SQLALchemy library connects Python with SQL (provides the interface)
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# The engine manages connections to the database 
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    # Open the csv document and read through it using csv.reader (build in in Python)
    f = open("books.csv")
    reader = csv.reader(f)

        # do not import th efirst row 
        next(csv_reader)

    # loop through the document naming the columns
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": isbn, "title": title, "author": author, "year": year})
        print(f"Added {title} from {author} year {year}.")
    db.commit()

if __name__ == "__main__":
    main()