import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz
import webbrowser
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

GENERAL_KEYWORDS = [
    "python", "sql", "javascript", "html", "css", "linux", "git", "api", 
    "soporte", "help desk", "windows", "redes", "hardware", "excel", "word",
    "ventas", "atencion al cliente", "administrativo", "logistica", "contable",
    "marketing", "seo", "redes sociales", "diseño", "photoshop", "illustrator",
    "java", "c++", "c#", "php", "ruby", "node", "react", "angular", "vue",
    "docker", "aws", "azure", "google cloud", "scrum", "agile", "jira",
    "ingles", "portugues", "frances", "liderazgo", "trabajo en equipo",
    "caja", "reposicion", "mostrador", "telefonista", "recepcion", "chofer"
]

PORTALES = {
    "LinkedIn": "https://www.linkedin.com/jobs/search/?keywords={}&location=Argentina&f_WT=2",
    "Indeed": "https://ar.indeed.com/jobs?q={}&l=Argentina",
    "Computrabajo": "https://www.computrabajo.com.ar/empleos-de-{}",
    "Bumeran": "https://www.bumeran.com.ar/empleos-busqueda-{}.html"
}

class PalaFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pala Finder 3000")
        self.geometry("700x700")
        self.cv_path = ""
        self.crear_interfaz()
        
    def crear_interfaz(self):
        self.label_titulo = ctk.CTkLabel(self, text="Pala Finder 3000", font=ctk.CTkFont(size=28, weight="bold"))
        self.label_titulo.pack(pady=15)
        
        frame_cv = ctk.CTkFrame(self)
        frame_cv.pack(pady=10, padx=20, fill="x")
        
        self.btn_seleccionar = ctk.CTkButton(frame_cv, text="Seleccionar CV (PDF)", command=self.seleccionar_cv, width=200, height=35)
        self.btn_seleccionar.grid(row=0, column=0, padx=10, pady=10)
        
        self.label_estado = ctk.CTkLabel(frame_cv, text="Ningún archivo seleccionado", text_color="gray")
        self.label_estado.grid(row=0, column=1, padx=10, pady=10)
        
        self.label_instruccion = ctk.CTkLabel(self, text="Skills detectadas (editables):", font=ctk.CTkFont(size=14))
        self.label_instruccion.pack(pady=5)
        
        self.text_skills = ctk.CTkTextbox(self, width=600, height=150)
        self.text_skills.pack(pady=10)
        self.text_skills.insert("0.0", "Cargá un CV para auto-detectar las skills...")
        
        frame_config = ctk.CTkFrame(self)
        frame_config.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(frame_config, text="Máximo de pestañas:").grid(row=0, column=0, padx=10, pady=10)
        self.limit_tabs = ctk.CTkComboBox(frame_config, values=["2", "3", "4", "5", "6", "8", "10"])
        self.limit_tabs.set("4")
        self.limit_tabs.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_config, text="Nuevo Portal (Nombre):").grid(row=1, column=0, padx=10, pady=5)
        self.entry_portal_name = ctk.CTkEntry(frame_config, placeholder_text="Ej: GetOnBoard")
        self.entry_portal_name.grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame_config, text="URL (usá {} para la skill):").grid(row=2, column=0, padx=10, pady=5)
        self.entry_portal_url = ctk.CTkEntry(frame_config, placeholder_text="https://.../empleos-{}")
        self.entry_portal_url.grid(row=2, column=1, padx=10, pady=5)
        
        self.btn_add_portal = ctk.CTkButton(frame_config, text="Agregar Portal", command=self.agregar_portal, width=150, height=30)
        self.btn_add_portal.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.btn_buscar = ctk.CTkButton(self, text="BUSCAR LABURO", command=self.buscar_laburo, width=250, height=45, fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_buscar.pack(pady=20)
        
    def seleccionar_cv(self):
        ruta = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if ruta:
            self.cv_path = ruta
            self.label_estado.configure(text=f"Archivo: {os.path.basename(ruta)}", text_color="white")
            self.analizar_cv()
            
    def analizar_cv(self):
        try:
            doc = fitz.open(self.cv_path)
            texto = "".join([pagina.get_text() for pagina in doc]).lower()
            doc.close()
            
            skills_detectadas = list(set([kw for kw in GENERAL_KEYWORDS if kw in texto]))
            
            self.text_skills.delete("0.0", "end")
            if skills_detectadas:
                self.text_skills.insert("0.0", ", ".join(skills_detectadas))
            else:
                self.text_skills.insert("0.0", "No se detectaron skills. Escribilas a mano separadas por coma.")
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el PDF:\n{e}")

    def agregar_portal(self):
        nombre = self.entry_portal_name.get().strip()
        url = self.entry_portal_url.get().strip()
        
        if nombre and url and "{}" in url:
            PORTALES[nombre] = url
            messagebox.showinfo("Éxito", f"Portal '{nombre}' agregado.")
            self.entry_portal_name.delete(0, 'end')
            self.entry_portal_url.delete(0, 'end')
        else:
            messagebox.showwarning("Error", "Completá los campos y asegurate de poner '{}' en la URL.")

    def buscar_laburo(self):
        texto_skills = self.text_skills.get("0.0", "end").strip()
        if not texto_skills or texto_skills.startswith("Cargá") or texto_skills.startswith("No se"):
            messagebox.showwarning("Faltan skills", "Escribí o detectá las skills primero.")
            return
        
        skills_a_buscar = [s.strip() for s in texto_skills.split(",") if s.strip()]
        limite = int(self.limit_tabs.get())
        total_abiertas = 0
        
        for skill in skills_a_buscar:
            if total_abiertas >= limite: 
                break
            skill_url = skill.replace(" ", "+")
            
            for portal, url_base in PORTALES.items():
                if total_abiertas >= limite: 
                    break
                url_final = url_base.format(skill_url)
                webbrowser.open(url_final)
                total_abiertas += 1
                
        messagebox.showinfo("Listo bo", f"Se abrieron {total_abiertas} pestañas. A aplicar.")

if __name__ == "__main__":
    app = PalaFinderApp()
    app.mainloop()