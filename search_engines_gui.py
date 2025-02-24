import tkinter as tk
from tkinter import messagebox
from tkinter import ttk  # For Progressbar
import subprocess
import json
import os
import threading

try:
    from search_engines import config
except ImportError as e:
    msg = '"{}"\nPlease install `search_engines` to resolve this error.'
    raise ImportError(msg.format(str(e)))


class SearchEngineGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Search Engine Scraper")
        self.root.geometry("600x400")

        # Label for query
        self.query_label = tk.Label(root, text="Enter Search Query:")
        self.query_label.pack(pady=10)

        # Entry for query
        self.query_entry = tk.Entry(root, width=50)
        self.query_entry.pack(pady=5)

        # Button to trigger the search
        self.search_button = tk.Button(root, text="Search", command=self.run_search)
        self.search_button.pack(pady=20)

        # Frame to display search results
        self.result_frame = tk.Frame(root)
        self.result_frame.pack(pady=10)

        # Pagination
        self.page_number = 1
        self.results_per_page = 10  # Set to 10 per page
        self.results_data = []

        # Pagination buttons
        self.prev_button = tk.Button(root, text="Previous", command=self.previous_page, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=10)
        self.next_button = tk.Button(root, text="Next", command=self.next_page)
        self.next_button.pack(side=tk.RIGHT, padx=10)

        # Progress bar
        self.progress = ttk.Progressbar(root, length=400, mode='indeterminate')
        self.progress.pack(pady=20)
        self.progress_label = tk.Label(root, text="")
        self.progress_label.pack()

    def run_search(self):
        query = self.query_entry.get()
        if not query:
            messagebox.showerror("Error", "Query is required!")
            return

        # Disable the search button to avoid multiple clicks
        self.search_button.config(state=tk.DISABLED)

        # Start the progress bar
        self.progress.start()
        self.progress_label.config(text="Searching...")

        # Fixed parameters as per argparse setup
        search_engine = "bing"  # Default search engine
        output_format = "json"  # Default output format (json)
        filename = "output"  # Default output filename
        pages = 5  # Query 5 pages by default
        filter_type = "title"  # Default filter
        ignore_duplicates = False  # Default flag for ignoring duplicates
        proxy = config.PROXY  # No proxy by default

        # Construct the command with arguments
        command = [
            "python", "search_engines_cli.py",
            "-q", query,
            "-e", search_engine,
            "-o", output_format,
            "-n", filename,
            "-p", str(pages),  # Query 5 pages by default
            "-f", filter_type,
            "-i" if ignore_duplicates else ""
        ]

        # Only add proxy if it's not empty
        if proxy:
            command.append("-proxy")
            command.append(proxy)

        # Remove any empty arguments
        command = [arg for arg in command if arg]

        # Run the command in a separate thread to avoid blocking UI
        search_thread = threading.Thread(target=self.run_command, args=(command, filename + ".json"))
        search_thread.start()

    def run_command(self, command, filename):
        try:
            # Run the script as a subprocess
            subprocess.run(command, check=True)

            # Parse and display the results after the command completes
            self.display_results(filename)

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")

        # Re-enable the search button after the process is complete
        self.search_button.config(state=tk.NORMAL)

        # Stop the progress bar and update label
        self.progress.stop()
        self.progress_label.config(text="Search Completed!")

    def display_results(self, filename):
        # Clear previous results
        for widget in self.result_frame.winfo_children():
            widget.grid_forget()

        if not os.path.exists(filename):
            messagebox.showerror("Error", "Output file does not exist.")
            return

        try:
            # Load JSON data from the output file
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)

            query = data.get("query", "No query")
            results = data.get("results", {})

            # Flatten results into a list of tuples containing search engine name and result details
            self.results_data = []
            for engine, engine_results in results.items():
                for result in engine_results:
                    # For each result, extract the relevant fields
                    title = result.get("title", "No Title")
                    link = result.get("link", "No Link")
                    host = result.get("host", "No Host")

                    # Add a dictionary with engine and result details to the results_data list
                    self.results_data.append({
                        "engine": engine,
                        "title": title,
                        "link": link,
                        "host": host
                    })

            self.page_number = 1

            # Display query
            query_label = tk.Label(self.result_frame, text=f"Results for: {query}", font=("Arial", 12, "bold"))
            query_label.grid(row=0, column=0, columnspan=3, pady=10)

            self.show_page()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse JSON: {e}")

    def show_page(self):
        # Clear previous results
        for widget in self.result_frame.winfo_children():
            widget.grid_forget()

        # Display results for the current page
        start_index = (self.page_number - 1) * self.results_per_page
        end_index = start_index + self.results_per_page
        page_results = self.results_data[start_index:end_index]

        # Table headers
        headers = ["Title", "Link", "Host"]
        for col, header in enumerate(headers):
            header_label = tk.Label(self.result_frame, text=header, font=("Arial", 10, "bold"))
            header_label.grid(row=1, column=col, padx=10)

        row = 2  # Start row for results
        for result in page_results:
            title = result.get("title", "No Title")
            link = result.get("link", "No Link")
            host = result.get("host", "No Host")

            tk.Label(self.result_frame, text=title, wraplength=200).grid(row=row, column=0)
            tk.Label(self.result_frame, text=link, wraplength=200).grid(row=row, column=1)
            tk.Label(self.result_frame, text=host, wraplength=200).grid(row=row, column=2)

            row += 1  # Move to the next row

        # Update the state of pagination buttons
        self.prev_button.config(state=tk.NORMAL if self.page_number > 1 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if end_index < len(self.results_data) else tk.DISABLED)

    def previous_page(self):
        if self.page_number > 1:
            self.page_number -= 1
            self.show_page()

    def next_page(self):
        if self.page_number * self.results_per_page < len(self.results_data):
            self.page_number += 1
            self.show_page()


if __name__ == "__main__":
    root = tk.Tk()
    app = SearchEngineGUI(root)
    root.mainloop()
