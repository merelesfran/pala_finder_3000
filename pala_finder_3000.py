import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import fitz
import webbrowser
import json
import os
import sqlite3
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def cargar_skills():
    try:
        with open('skills.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("No se encontró skills.json")
        return {}

def cargar_perfiles():
    perfiles = {}
    try:
        with open('profiles.json', 'r', encoding='utf-8') as f:
            perfiles.update(json.load(f))
    except FileNotFoundError:
        print("No se encontró profiles.json")
    
    try:
        with open('custom_profiles.json', 'r', encoding='utf-8') as f:
            perfiles.update(json.load(f))
    except FileNotFoundError:
        pass
    
    return perfiles

def guardar_perfiles_custom(perfiles_custom):
    with open('custom_profiles.json', 'w', encoding='utf-8') as f:
        json.dump(perfiles_custom, f, indent=4, ensure_ascii=False)

def init_db():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS busquedas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            portal TEXT,
            skill_buscada TEXT,
            url TEXT,
            favorito INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def guardar_busqueda(portal, skill, url):
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO busquedas (fecha, portal, skill_buscada, url) VALUES (?, ?, ?, ?)',
        (datetime.now().strftime('%Y-%m-%d %H:%M'), portal, skill, url)
    )
    conn.commit()
    conn.close()

def obtener_historial():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fecha, portal, skill_buscada, url, favorito FROM busquedas ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def limpiar_historial():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM busquedas')
    conn.commit()
    conn.close()

SKILL_ALIASES = cargar_skills()
PERFILES = cargar_perfiles()
GENERAL_KEYWORDS = list(SKILL_ALIASES.keys()) if SKILL_ALIASES else []

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
        self.geometry("850x950")
        self.cv_path = ""
        self.cv_skills = set()
        init_db()
        self.crear_interfaz()
        
    def crear_interfaz(self):
        self.label_titulo = ctk.CTkLabel(self, text="Pala Finder 3000", font=ctk.CTkFont(size=28, weight="bold"))
        self.label_titulo.pack(pady=10)
        
        frame_cv = ctk.CTkFrame(self)
        frame_cv.pack(pady=10, padx=20, fill="x")
        
        self.btn_seleccionar = ctk.CTkButton(frame_cv, text="Seleccionar CV (PDF)", command=self.seleccionar_cv, width=200, height=35)
        self.btn_seleccionar.grid(row=0, column=0, padx=10, pady=10)
        
        self.label_estado = ctk.CTkLabel(frame_cv, text="Ningún archivo seleccionado", text_color="gray")
        self.label_estado.grid(row=0, column=1, padx=10, pady=10)
        
        if PERFILES:
            frame_perfil = ctk.CTkFrame(self)
            frame_perfil.pack(pady=10, padx=20, fill="x")
            
            ctk.CTkLabel(frame_perfil, text="Perfil objetivo:").grid(row=0, column=0, padx=10, pady=10)
            self.combo_perfil = ctk.CTkComboBox(frame_perfil, values=list(PERFILES.keys()), command=self.calcular_match)
            self.combo_perfil.set("Seleccionar perfil...")
            self.combo_perfil.grid(row=0, column=1, padx=10, pady=10)
            
            self.btn_crear_perfil = ctk.CTkButton(frame_perfil, text="Crear Perfil", command=self.crear_perfil, width=120, height=30)
            self.btn_crear_perfil.grid(row=0, column=2, padx=10, pady=10)
        
        self.label_instruccion = ctk.CTkLabel(self, text="Skills detectadas (editables):", font=ctk.CTkFont(size=14))
        self.label_instruccion.pack(pady=5)
        
        self.text_skills = ctk.CTkTextbox(self, width=700, height=100)
        self.text_skills.pack(pady=5)
        self.text_skills.insert("0.0", "Cargá un CV para auto-detectar las skills...")
        self.text_skills.configure(state="disabled")
        
        self.frame_match = ctk.CTkFrame(self)
        self.frame_match.pack(pady=5, padx=20, fill="x")
        
        self.label_match_score = ctk.CTkLabel(self.frame_match, text="Match Score: --%", font=ctk.CTkFont(size=18, weight="bold"))
        self.label_match_score.pack(pady=3)
        
        self.label_match_details = ctk.CTkLabel(self.frame_match, text="", justify="left")
        self.label_match_details.pack(pady=3)
        
        frame_config = ctk.CTkFrame(self)
        frame_config.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(frame_config, text="Máximo de pestañas:").grid(row=0, column=0, padx=10, pady=5)
        self.limit_tabs = ctk.CTkComboBox(frame_config, values=["2", "3", "4", "5", "6", "8", "10"])
        self.limit_tabs.set("4")
        self.limit_tabs.grid(row=0, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame_config, text="Nuevo Portal (Nombre):").grid(row=1, column=0, padx=10, pady=3)
        self.entry_portal_name = ctk.CTkEntry(frame_config, placeholder_text="Ej: GetOnBoard")
        self.entry_portal_name.grid(row=1, column=1, padx=10, pady=3)
        
        ctk.CTkLabel(frame_config, text="URL (usá {} para la skill):").grid(row=2, column=0, padx=10, pady=3)
        self.entry_portal_url = ctk.CTkEntry(frame_config, placeholder_text="https://.../empleos-{}")
        self.entry_portal_url.grid(row=2, column=1, padx=10, pady=3)
        
        self.btn_add_portal = ctk.CTkButton(frame_config, text="Agregar Portal", command=self.agregar_portal, width=150, height=28)
        self.btn_add_portal.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.btn_buscar = ctk.CTkButton(self, text="BUSCAR LABURO", command=self.buscar_laburo, width=250, height=40, fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_buscar.pack(pady=10)
        
        # Historial
        frame_historial = ctk.CTkFrame(self)
        frame_historial.pack(pady=10, padx=20, fill="both", expand=True)
        
        frame_historial_header = ctk.CTkFrame(frame_historial)
        frame_historial_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(frame_historial_header, text="Historial de Búsquedas", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10)
        
        self.btn_limpiar = ctk.CTkButton(frame_historial_header, text="Limpiar", command=self.limpiar_historial_gui, width=80, height=25, fg_color="#dc3545", hover_color="#c82333")
        self.btn_limpiar.pack(side="right", padx=10)
        
        self.tree = ttk.Treeview(frame_historial, columns=("fecha", "portal", "skill", "url"), show="headings", height=8)
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("portal", text="Portal")
        self.tree.heading("skill", text="Skill")
        self.tree.heading("url", text="URL")
        
        self.tree.column("fecha", width=120)
        self.tree.column("portal", width=100)
        self.tree.column("skill", width=120)
        self.tree.column("url", width=400)
        
        scrollbar = ttk.Scrollbar(frame_historial, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        self.cargar_historial_gui()
        
    def cargar_historial_gui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        historial = obtener_historial()
        for row in historial:
            fecha, portal, skill, url, favorito = row
            icono = "★" if favorito else ""
            self.tree.insert("", "end", values=(f"{fecha} {icono}", portal, skill, url))
    
    def limpiar_historial_gui(self):
        if messagebox.askyesno("Confirmar", "¿Seguro que querés borrar todo el historial?"):
            limpiar_historial()
            self.cargar_historial_gui()
        
    def crear_perfil(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Crear Perfil Personalizado")
        ventana.geometry("500x500")
        ventana.grab_set()
        
        ctk.CTkLabel(ventana, text="Nombre del Perfil:", font=ctk.CTkFont(size=14)).pack(pady=10)
        entry_nombre = ctk.CTkEntry(ventana, width=300, placeholder_text="Ej: Contador Senior")
        entry_nombre.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Skills Requeridas (separadas por coma):", font=ctk.CTkFont(size=12)).pack(pady=10)
        text_requeridas = ctk.CTkTextbox(ventana, width=400, height=80)
        text_requeridas.pack(pady=5)
        text_requeridas.insert("0.0", "excel, contable, sql")
        
        ctk.CTkLabel(ventana, text="Skills Deseables (separadas por coma):", font=ctk.CTkFont(size=12)).pack(pady=10)
        text_deseables = ctk.CTkTextbox(ventana, width=400, height=80)
        text_deseables.pack(pady=5)
        text_deseables.insert("0.0", "sap, power bi, inglés")
        
        def guardar():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showwarning("Error", "El nombre del perfil es obligatorio")
                return
            
            skills_req = [s.strip() for s in text_requeridas.get("0.0", "end").split(",") if s.strip()]
            skills_des = [s.strip() for s in text_deseables.get("0.0", "end").split(",") if s.strip()]
            
            if not skills_req:
                messagebox.showwarning("Error", "Agregá al menos una skill requerida")
                return
            
            try:
                with open('custom_profiles.json', 'r', encoding='utf-8') as f:
                    custom_profiles = json.load(f)
            except FileNotFoundError:
                custom_profiles = {}
            
            custom_profiles[nombre] = {
                "skills_requeridas": skills_req,
                "skills_deseables": skills_des,
                "experiencia_minima": "Personalizado",
                "seniority": "Personalizado"
            }
            
            guardar_perfiles_custom(custom_profiles)
            PERFILES.update(custom_profiles)
            self.combo_perfil.configure(values=list(PERFILES.keys()))
            
            messagebox.showinfo("Éxito", f"Perfil '{nombre}' creado correctamente")
            ventana.destroy()
        
        btn_guardar = ctk.CTkButton(ventana, text="Guardar Perfil", command=guardar, width=200, height=35)
        btn_guardar.pack(pady=20)
        
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
            
            skills_detectadas = set()
            for skill_base, aliases in SKILL_ALIASES.items():
                if skill_base in texto:
                    skills_detectadas.add(skill_base)
                for alias in aliases:
                    if alias in texto:
                        skills_detectadas.add(skill_base)
                        break
            
            self.cv_skills = skills_detectadas
            
            self.text_skills.configure(state="normal")
            self.text_skills.delete("0.0", "end")
            if skills_detectadas:
                self.text_skills.insert("0.0", ", ".join(sorted(skills_detectadas)))
            else:
                self.text_skills.insert("0.0", "No se detectaron skills. Escribilas a mano separadas por coma.")
            self.text_skills.configure(state="normal")
            
            self.calcular_match()
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el PDF:\n{e}")

    def calcular_match(self, event=None):
        if not self.cv_skills or not PERFILES:
            return
        
        perfil_seleccionado = self.combo_perfil.get()
        if perfil_seleccionado not in PERFILES:
            return
        
        perfil = PERFILES[perfil_seleccionado]
        skills_requeridas = set(perfil["skills_requeridas"])
        skills_deseables = set(perfil["skills_deseables"])
        
        skills_encontradas_req = skills_requeridas.intersection(self.cv_skills)
        skills_encontradas_des = skills_deseables.intersection(self.cv_skills)
        
        skills_faltantes_req = skills_requeridas - self.cv_skills
        skills_faltantes_des = skills_deseables - self.cv_skills
        
        score_requeridas = len(skills_encontradas_req) / len(skills_requeridas) * 70 if skills_requeridas else 0
        score_deseables = len(skills_encontradas_des) / len(skills_deseables) * 30 if skills_deseables else 0
        match_percentage = int(score_requeridas + score_deseables)
        
        self.label_match_score.configure(text=f"Match Score: {match_percentage}%")
        
        details = f"✓ Skills requeridas: {', '.join(sorted(skills_encontradas_req)) if skills_encontradas_req else 'Ninguna'}\n"
        details += f"✗ Faltan: {', '.join(sorted(skills_faltantes_req)) if skills_faltantes_req else 'Ninguna'}\n"
        details += f"★ Deseables: {', '.join(sorted(skills_encontradas_des)) if skills_encontradas_des else 'Ninguna'}"
        
        self.label_match_details.configure(text=details)

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
                guardar_busqueda(portal, skill, url_final)
                total_abiertas += 1
        
        self.cargar_historial_gui()
        messagebox.showinfo("Listo bo", f"Se abrieron {total_abiertas} pestañas. A aplicar.")

if __name__ == "__main__":
    app = PalaFinderApp()
    app.mainloop()