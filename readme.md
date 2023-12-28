# Project Overview

This project is a content creation system that scrapes news articles from websites, summarizes the articles, and stores 
the summarized content in a database. The system is designed to be modular, allowing for different scraping, summarizing, and database management strategies to be used interchangeably.

## Key Components

### News Scraper

The news scraper is responsible for extracting article URLs from a homepage and extracting text and images from each 
article URL. The `NewsScraper` class is an abstract base class that defines the interface for all news scrapers. 
The `ScraperRtvSlo` class is a concrete implementation of the `NewsScraper` interface for the RTVSlo website.

### Summarizer

The summarizer is responsible for generating a headline and summary for each article. The `BaseSummarizer` class is an abstract base
class that defines the interface for all summarizers. The `ChatGPTSummarizer` and `SloT5Summarizer` classes are concrete implementations
of the `BaseSummarizer` interface. The SloT5Summarizer uses custom slovenian summarizer model.

### Database Manager

The database manager is responsible for writing the summarized content to a database and managing the priority of each article. 
The `DatabaseManager` class is an abstract base class that defines the interface for all database managers. 
The `PostgresDbManager` and `MSSQLLocalDbManager` classes are concrete implementations of the DatabaseManager interface.

### Content Creator

The `NoviceContentCreator` class coordinates the news scraper, summarizer, and database manager to create content. 
It extracts URLs from the homepage, summarizes each article, and writes the summarized content to the database.

## Dependencies

The project has several dependencies, which are listed in the `requirements.txt` file. 
These include requests, bs4, beautifulsoup4, selenium, psycopg2, and pyodbc.

## Running the Project

The main entry point for the project is the main-cli.py file. When run, it creates a NoviceContentCreator instance and calls its create_content method.