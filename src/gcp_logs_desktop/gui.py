from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import BooleanVar, END, Listbox, MULTIPLE, StringVar, Tk, filedialog, messagebox, ttk
from typing import Any

from .app_service import capture_logs
from .auth import load_credentials
from .config import CaptureConfig
from .projects import GcpProject, list_available_projects


class BigQueryLogsApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("GCP BigQuery Logs Capture")
        self.root.minsize(820, 560)

        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.credentials: Any | None = None
        self.available_projects: list[GcpProject] = []

        self.auth_mode = StringVar(value="adc")
        self.service_account_file = StringVar(value="")
        self.output_format = StringVar(value="csv")
        self.anonymize_email = BooleanVar(value=True)
        self.hash_query_text = BooleanVar(value=True)
        self.status = StringVar(value="Ready")

        self.main = ttk.Frame(self.root, padding=16)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.auth_button: ttk.Button | None = None
        self.capture_button: ttk.Button | None = None
        self.projects_listbox: Listbox | None = None

        self._show_auth_page()
        self._poll_messages()

    def _clear_main(self) -> None:
        for child in self.main.winfo_children():
            child.destroy()
        self.main.columnconfigure(0, weight=0)
        self.main.columnconfigure(1, weight=1)
        self.main.rowconfigure(3, weight=0)

    def _show_auth_page(self) -> None:
        self._clear_main()
        self.status.set("Authenticate with Google Cloud to discover available projects.")

        ttk.Label(self.main, text="Step 1: Authenticate with GCP", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )

        ttk.Label(self.main, text="Authentication method").grid(row=1, column=0, sticky="w", pady=6)
        auth_frame = ttk.Frame(self.main)
        auth_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=6)
        ttk.Radiobutton(auth_frame, text="Automatic browser sign-in with gcloud", variable=self.auth_mode, value="adc").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Radiobutton(auth_frame, text="Service account JSON", variable=self.auth_mode, value="service_account").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        ttk.Label(self.main, text="Service account file").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(self.main, textvariable=self.service_account_file).grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Button(self.main, text="Browse...", command=self._choose_service_account).grid(
            row=2, column=2, padx=(8, 0), pady=6
        )

        self.auth_button = ttk.Button(self.main, text="Authenticate and load projects", command=self._start_authentication)
        self.auth_button.grid(row=3, column=1, sticky="w", pady=(18, 8))

        ttk.Label(
            self.main,
            text="The gcloud option opens the Google sign-in browser automatically when credentials are missing.",
        ).grid(row=4, column=1, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(self.main, textvariable=self.status).grid(row=5, column=0, columnspan=3, sticky="ew", pady=(12, 0))

    def _show_project_page(self) -> None:
        self._clear_main()
        self.main.rowconfigure(2, weight=1)
        self.status.set(f"Authenticated. Select one or more projects from {len(self.available_projects)} available projects.")

        ttk.Label(self.main, text="Step 2: Select projects and capture logs", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )
        ttk.Button(self.main, text="Change authentication", command=self._reset_authentication).grid(
            row=0, column=2, sticky="e", pady=(0, 12)
        )

        ttk.Label(self.main, text="Available projects").grid(row=1, column=0, sticky="nw", pady=6)
        list_frame = ttk.Frame(self.main)
        list_frame.grid(row=1, column=1, columnspan=2, rowspan=2, sticky="nsew", pady=6)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.projects_listbox = Listbox(list_frame, selectmode=MULTIPLE, height=12, exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.projects_listbox.yview)
        self.projects_listbox.configure(yscrollcommand=scrollbar.set)
        self.projects_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        for project in self.available_projects:
            self.projects_listbox.insert(END, project.label)

        select_buttons = ttk.Frame(self.main)
        select_buttons.grid(row=3, column=1, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Button(select_buttons, text="Select all", command=self._select_all_projects).grid(row=0, column=0, sticky="w")
        ttk.Button(select_buttons, text="Clear selection", command=self._clear_project_selection).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )

        ttk.Separator(self.main).grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 14))

        ttk.Label(
            self.main,
            text='The API query matches the Fabric notebook: last 30 days, resource.type="bigquery_resource", severity=INFO, methodName="jobservice.jobcompleted".',
        ).grid(row=5, column=1, columnspan=2, sticky="w", pady=(0, 8))

        options = ttk.Frame(self.main)
        options.grid(row=6, column=1, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Checkbutton(options, text="Hash principalEmail", variable=self.anonymize_email).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="Hash query literals", variable=self.hash_query_text).grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )

        ttk.Label(self.main, text="Output format").grid(row=7, column=0, sticky="w", pady=(12, 4))
        ttk.Combobox(
            self.main,
            textvariable=self.output_format,
            values=("csv", "parquet"),
            width=10,
            state="readonly",
        ).grid(row=7, column=1, sticky="w", pady=(12, 4))

        self.capture_button = ttk.Button(
            self.main,
            text="Execute log capture...",
            command=self._choose_output_and_start_capture,
        )
        self.capture_button.grid(row=8, column=1, sticky="w", pady=(18, 8))

        ttk.Label(self.main, textvariable=self.status).grid(row=9, column=0, columnspan=3, sticky="ew", pady=(12, 0))

    def _choose_service_account(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select service account JSON",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if filename:
            self.service_account_file.set(filename)

    def _start_authentication(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        try:
            service_account_file = self._service_account_path()
        except ValueError as exc:
            messagebox.showerror("Invalid authentication configuration", str(exc))
            return

        if self.auth_button is not None:
            self.auth_button.configure(state="disabled")
        if self.auth_mode.get() == "adc":
            self.status.set("Authenticating with Google Cloud. A browser window may open automatically...")
        else:
            self.status.set("Authenticating with Google Cloud...")
        self.worker = threading.Thread(
            target=self._authenticate_and_load_projects,
            args=(self.auth_mode.get(), service_account_file),
            daemon=True,
        )
        self.worker.start()

    def _service_account_path(self) -> Path | None:
        if self.auth_mode.get() != "service_account":
            return None
        value = self.service_account_file.get().strip()
        if not value:
            raise ValueError("Select a service account JSON file or choose browser user sign-in.")
        path = Path(value)
        if not path.exists():
            raise ValueError(f"Service account file does not exist: {path}")
        return path

    def _authenticate_and_load_projects(
        self,
        auth_mode: str,
        service_account_file: Path | None,
    ) -> None:
        try:
            credentials = load_credentials(auth_mode, service_account_file)
            self.messages.put(("status", "Authentication succeeded. Loading available projects..."))
            projects = list_available_projects(credentials)
            if not projects:
                raise ValueError("No active GCP projects were returned for the authenticated account.")
        except Exception as exc:
            self.messages.put(("auth_error", exc))
        else:
            self.messages.put(("auth_done", (credentials, projects)))

    def _reset_authentication(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.credentials = None
        self.available_projects = []
        self._show_auth_page()

    def _select_all_projects(self) -> None:
        if self.projects_listbox is not None:
            self.projects_listbox.select_set(0, END)

    def _clear_project_selection(self) -> None:
        if self.projects_listbox is not None:
            self.projects_listbox.selection_clear(0, END)

    def _selected_project_resource_names(self) -> list[str]:
        if self.projects_listbox is None:
            return []
        indexes = [int(index) for index in self.projects_listbox.curselection()]
        return [self.available_projects[index].resource_name for index in indexes]

    def _choose_output_and_start_capture(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        if self.credentials is None:
            messagebox.showerror("Not authenticated", "Authenticate with Google Cloud before capturing logs.")
            return

        selected_projects = self._selected_project_resource_names()
        if not selected_projects:
            messagebox.showerror("No projects selected", "Select at least one project before capturing logs.")
            return

        output_path = self._ask_output_path()
        if output_path is None:
            return

        try:
            config = self._read_capture_config(selected_projects, output_path)
        except ValueError as exc:
            messagebox.showerror("Invalid capture configuration", str(exc))
            return

        if self.capture_button is not None:
            self.capture_button.configure(state="disabled")
        self.status.set("Starting log capture...")
        self.worker = threading.Thread(target=self._run_capture, args=(config,), daemon=True)
        self.worker.start()

    def _ask_output_path(self) -> Path | None:
        extension = self.output_format.get()
        filename = filedialog.asksaveasfilename(
            title="Choose where to store the captured logs",
            defaultextension=f".{extension}",
            initialfile=f"bq_logs.{extension}",
            filetypes=((f"{extension.upper()} files", f"*.{extension}"), ("All files", "*.*")),
        )
        return Path(filename) if filename else None

    def _read_capture_config(self, selected_projects: list[str], output_path: Path) -> CaptureConfig:
        config = CaptureConfig(
            auth_mode=self.auth_mode.get(),
            service_account_file=self._service_account_path(),
            projects=selected_projects,
            output_format=self.output_format.get(),
            output_path=output_path,
            anonymize_email=bool(self.anonymize_email.get()),
            hash_query_text=bool(self.hash_query_text.get()),
        )
        config.validate()
        return config

    def _run_capture(self, config: CaptureConfig) -> None:
        try:
            result = capture_logs(
                config,
                status_callback=lambda message: self.messages.put(("status", message)),
                progress_callback=lambda count: self.messages.put(("progress", count)),
                credentials=self.credentials,
            )
        except Exception as exc:
            self.messages.put(("capture_error", exc))
        else:
            self.messages.put(("capture_done", (result.row_count, result.output_path)))

    def _poll_messages(self) -> None:
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break

            if kind == "status":
                self.status.set(str(payload))
            elif kind == "progress":
                self.status.set(f"Processed {payload} log entries...")
            elif kind == "auth_error":
                if self.auth_button is not None:
                    self.auth_button.configure(state="normal")
                self.status.set("Authentication failed")
                messagebox.showerror("Authentication failed", str(payload))
            elif kind == "auth_done":
                self.credentials, self.available_projects = payload  # type: ignore[assignment]
                self._show_project_page()
            elif kind == "capture_error":
                if self.capture_button is not None:
                    self.capture_button.configure(state="normal")
                self.status.set("Capture failed")
                messagebox.showerror("Capture failed", str(payload))
            elif kind == "capture_done":
                count, output_path = payload  # type: ignore[misc]
                if self.capture_button is not None:
                    self.capture_button.configure(state="normal")
                self.status.set(f"Done. Exported {count} rows.")
                messagebox.showinfo("Capture complete", f"Exported {count} rows to {output_path}")

        self.root.after(250, self._poll_messages)


def main() -> None:
    root = Tk()
    BigQueryLogsApp(root)
    root.mainloop()
