Python script to keep track of temperature and humidity information from Verisure sensors in the house

- uses webscraping to login to Verisure and get sensor information from the min_side page
- extracts relevant information
- write it to a google docs spreadsheet
- sensor names and spreadsheet sheetname are hardcoded (see TODO)

- Uses following modules:
	- requests and beautifulsoup to scrape the webpage
	- gspread to write to gdrive spreadsheet

Installation
- copy config file template to climateSensors.config
- add relavant usernames and passwords
- DO NOT change last_timestamp (it is updated with the last recorded sensor data from verisure

TODO:
- update logging to file
- move sensor names and number to config file
- move spreadsheet sheetname to config file
- add humidity and temperature observations (outdoors) from yr.no
- write to local db rather than gspread
