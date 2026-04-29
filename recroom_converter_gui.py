import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from convert_recroom_avatar import (
    ConversionRequest,
    append_log_line,
    find_blender,
    load_config,
    resolve_vrm_addon_source,
    run_conversion,
)


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Rec Room VRM Converter")
        self.root.geometry("900x620")

        self.config = load_config(None)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.input_var = tk.StringVar(master=self.root)
        self.output_var = tk.StringVar(master=self.root)
        self.blender_var = tk.StringVar(master=self.root, value=self._default_blender())
        self.addon_var = tk.StringVar(master=self.root, value=self._default_addon())
        self.keep_blend_var = tk.BooleanVar(master=self.root, value=True)

        self._build_ui()
        self.root.after(100, self._drain_log_queue)

    def _default_blender(self) -> str:
        try:
            return str(find_blender(None, self.config))
        except FileNotFoundError:
            return ""

    def _default_addon(self) -> str:
        source = resolve_vrm_addon_source(None, self.config)
        return str(source) if source else ""

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        self._path_row(frame, 0, "Input GLB", self.input_var, self._browse_input)
        self._path_row(frame, 1, "Output VRM", self.output_var, self._browse_output)
        self._path_row(frame, 2, "Blender", self.blender_var, self._browse_blender)
        self._path_row(frame, 3, "VRM Addon", self.addon_var, self._browse_addon)

        ttk.Checkbutton(
            frame,
            text="Keep intermediate .blend file",
            variable=self.keep_blend_var,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 8))

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=2, sticky="e")
        self.run_button = ttk.Button(button_row, text="Convert", command=self._start)
        self.run_button.pack(side="left")

        self.status_var = tk.StringVar(master=self.root, value="Ready")
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(4, 4)
        )

        self.log_text = tk.Text(frame, wrap="word", height=24)
        self.log_text.grid(row=6, column=0, columnspan=3, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=6, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _path_row(
        self,
        frame: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        browse_command: callable,
    ) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=(8, 8), pady=4
        )
        ttk.Button(frame, text="Browse", command=browse_command).grid(
            row=row, column=2, sticky="e", pady=4
        )

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Rec Room GLB",
            filetypes=[("glTF Binary", "*.glb")],
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                self.output_var.set(str(Path(path).with_suffix(".vrm")))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select Output VRM",
            defaultextension=".vrm",
            filetypes=[("VRM", "*.vrm")],
        )
        if path:
            self.output_var.set(path)

    def _browse_blender(self) -> None:
        path = filedialog.askopenfilename(
            title="Select blender.exe",
            filetypes=[("Blender", "blender.exe"), ("Executable", "*.exe")],
        )
        if path:
            self.blender_var.set(path)

    def _browse_addon(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select VRM Addon Zip",
            filetypes=[("Zip", "*.zip"), ("All files", "*.*")],
        )
        if file_path:
            self.addon_var.set(file_path)
            return
        dir_path = filedialog.askdirectory(title="Select VRM Addon Folder")
        if dir_path:
            self.addon_var.set(dir_path)

    def _make_request(self) -> ConversionRequest:
        input_path = Path(self.input_var.get()).resolve()
        output_path = Path(self.output_var.get()).resolve()
        blender_path = Path(self.blender_var.get()).resolve()
        addon_text = self.addon_var.get().strip()
        addon_path = Path(addon_text).resolve() if addon_text else None

        if not input_path.is_file():
            raise FileNotFoundError("Input GLB was not found.")
        if output_path.suffix.lower() != ".vrm":
            raise ValueError("Output file must use the .vrm extension.")
        if not blender_path.is_file():
            raise FileNotFoundError("Blender executable was not found.")
        if addon_path and not addon_path.exists():
            raise FileNotFoundError("VRM addon source was not found.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        return ConversionRequest(
            input_glb=input_path,
            output_vrm=output_path,
            blender_path=blender_path,
            keep_blend=bool(self.keep_blend_var.get()),
            skip_vrm=False,
            vrm_addon_source=addon_path,
        )

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            request = self._make_request()
        except Exception as exc:
            messagebox.showerror("Invalid Input", str(exc))
            return

        self.log_text.delete("1.0", "end")
        self.run_button.configure(state="disabled")
        self.status_var.set("Converting...")

        def task() -> None:
            try:
                exit_code = run_conversion(request, self.log_queue.put)
                if exit_code == 0:
                    self.log_queue.put(f"SUCCESS: {request.output_vrm}")
                else:
                    self.log_queue.put(f"FAILED: exit code {exit_code}")
                    self.log_queue.put("See RecRoomVrmConverter.log for details.")
            except Exception as exc:
                append_log_line(f"GUI worker error: {exc}")
                self.log_queue.put(f"ERROR: {exc}")
            finally:
                self.log_queue.put("__DONE__")

        self.worker = threading.Thread(target=task, daemon=True)
        self.worker.start()

    def _drain_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if line == "__DONE__":
                self.run_button.configure(state="normal")
                self.status_var.set("Finished")
                continue
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
        self.root.after(100, self._drain_log_queue)


def main() -> int:
    try:
        root = tk.Tk()
        app = ConverterApp(root)
        root.mainloop()
        return 0
    except Exception as exc:
        append_log_line(f"GUI startup error: {exc}")
        try:
            messagebox.showerror(
                "Rec Room VRM Converter",
                f"Startup failed.\n\nSee RecRoomVrmConverter.log for details.\n\n{exc}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
