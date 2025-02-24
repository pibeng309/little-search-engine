import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import json
import os
import threading
import webbrowser

try:
    from search_engines import config
except ImportError as e:
    msg = '"{}"\nPlease install `search_engines` to resolve this error.'
    raise ImportError(msg.format(str(e)))


class ModernSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Next Search")
        self.root.geometry("1280x720")
        self.root.configure(bg="#ffffff")

        # 现代LOGO展示
        self.logo_frame = tk.Frame(root, bg="#ffffff")
        self.logo_frame.pack(pady=(120, 50))
        self.logo_label = tk.Label(self.logo_frame,
                                   text="NEXT",
                                   font=("Roboto", 48, "bold"),
                                   fg="#4285f4",
                                   bg="#ffffff")
        self.logo_label.pack(side=tk.LEFT)
        tk.Label(self.logo_frame,
                 text="SEARCH",
                 font=("Roboto", 48),
                 fg="#5f6368",
                 bg="#ffffff").pack(side=tk.LEFT)

        # 智能搜索框
        self.search_frame = tk.Frame(root, bg="#ffffff")
        self.search_frame.pack()
        self.query_entry = tk.Entry(self.search_frame,
                                    width=80,
                                    font=("Arial", 16),
                                    relief="flat",
                                    highlightthickness=1,
                                    highlightcolor="#4285f4",
                                    highlightbackground="#dfe1e5")
        self.query_entry.pack(pady=10)
        self.query_entry.bind("<Return>", lambda e: self.run_search())

        # 动态搜索按钮
        self.btn_frame = tk.Frame(root, bg="#ffffff")
        self.btn_frame.pack()
        self.search_button = tk.Button(self.btn_frame,
                                       text="Search",
                                       command=self.run_search,
                                       bg="#4285f4",
                                       fg="white",
                                       activebackground="#357abd",
                                       borderwidth=0,
                                       font=("Arial", 14),
                                       padx=32,
                                       pady=12)
        self.search_button.pack()

        # 交互效果增强
        self.search_button.bind("<Enter>", lambda e: self.search_button.config(bg="#357abd"))
        self.search_button.bind("<Leave>", lambda e: self.search_button.config(bg="#4285f4"))

        # 智能结果容器
        self.result_container = tk.Canvas(root, bg="#ffffff", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.result_container.yview)
        self.result_frame = tk.Frame(self.result_container, bg="#ffffff")

        # 将结果框架放入画布中
        self.result_container.create_window((0, 0), window=self.result_frame, anchor="nw")
        self.result_container.configure(yscrollcommand=self.scrollbar.set)

        # 分页系统
        self.pagination_frame = tk.Frame(root, bg="#ffffff")
        self.prev_btn = self.create_pagination_btn("‹ Previous", self.previous_page)
        self.page_label = tk.Label(self.pagination_frame, text="Page 1", fg="#70757a", bg="#ffffff")
        self.next_btn = self.create_pagination_btn("Next ›", self.next_page)

        # 进度指示器
        self.progress = ttk.Progressbar(root, length=400, mode="indeterminate")
        self.status_label = tk.Label(root, text="", fg="#5f6368", bg="#ffffff")

        # 初始化数据
        self.page_number = 1
        self.results_per_page = 10
        self.results_data = []

        # 布局
        self.result_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pagination_frame.pack(pady=20)
        self.prev_btn.pack(side=tk.LEFT, padx=10)
        self.page_label.pack(side=tk.LEFT)
        self.next_btn.pack(side=tk.LEFT, padx=10)

        self.progress.pack(pady=20)
        self.status_label.pack()

        # 绑定滚动条和画布
        self.result_frame.bind("<Configure>", self.on_frame_configure)

    def create_pagination_btn(self, text, command):
        return tk.Button(self.pagination_frame,
                         text=text,
                         command=command,
                         fg="#4285f4",
                         bg="#ffffff",
                         activeforeground="#357abd",
                         borderwidth=0,
                         font=("Arial", 12))

    def run_search(self):
        query = self.query_entry.get()
        if not query:
            messagebox.showerror("Error", "Query is required!")
            return

        # Disable the search button to avoid multiple clicks
        self._toggle_ui_state(False)

        # Start the progress bar
        self.progress.start()
        self.status_label.config(text="Searching the web...")

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

    def _toggle_ui_state(self, enabled=True):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.search_button.config(state=state)
        self.query_entry.config(state=state)

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
        self._toggle_ui_state(True)

        # Stop the progress bar and update label
        self.progress.stop()
        self.status_label.config(text="Search Completed!")

    def display_results(self, filename):
        # Clear previous results
        for widget in self.result_frame.winfo_children():
            widget.destroy()

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
            query_label = tk.Label(self.result_frame, text=f"Results for: {query}", font=("Arial", 12, "bold"),
                                   bg="#ffffff")
            query_label.pack(pady=10)

            self.show_page()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse JSON: {e}")

    def show_page(self):
        # Clear previous results
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        # Display results for the current page
        start_index = (self.page_number - 1) * self.results_per_page
        end_index = start_index + self.results_per_page
        page_results = self.results_data[start_index:end_index]

        # 显示结果项
        for idx, result in enumerate(page_results):
            result_frame = tk.Frame(self.result_frame, bg="#ffffff", padx=20, pady=12)
            result_frame.pack(fill=tk.X, pady=8)

            # 可点击标题
            title = tk.Label(result_frame,
                             text=result["title"],
                             fg="#1a0dab",
                             font=("Arial", 14),
                             cursor="hand2",
                             bg="#ffffff")
            title.pack(anchor="w")
            title.bind("<Button-1>", lambda e, url=result["link"]: self.open_url(url))

            # URL展示
            tk.Label(result_frame,
                     text=result["link"],
                     fg="#006621",
                     font=("Arial", 12),
                     bg="#ffffff").pack(anchor="w")

            # 描述文本
            tk.Label(result_frame,
                     text=f"{result['host']} - Sample description text...",
                     fg="#545454",
                     font=("Arial", 12),
                     wraplength=1000,
                     justify="left",
                     bg="#ffffff").pack(anchor="w")

            # 动态分割线
            if idx != len(page_results) - 1:
                ttk.Separator(result_frame, orient="horizontal").pack(fill=tk.X, pady=8)

        # 更新分页系统
        self._update_pagination()

    def open_url(self, url):
        webbrowser.open(url)

    def _update_pagination(self):
        self.page_label.config(text=f"Page {self.page_number}")
        self.prev_btn.config(state=tk.NORMAL if self.page_number > 1 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.has_more_pages() else tk.DISABLED)

    def previous_page(self):
        if self.page_number > 1:
            self.page_number -= 1
            self.show_page()

    def next_page(self):
        if self.page_number * self.results_per_page < len(self.results_data):
            self.page_number += 1
            self.show_page()

    def has_more_pages(self):
        return self.page_number * self.results_per_page < len(self.results_data)

    def on_frame_configure(self, event):
        self.result_container.configure(scrollregion=self.result_container.bbox("all"))


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernSearchGUI(root)
    root.mainloop()