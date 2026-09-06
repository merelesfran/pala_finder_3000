import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pymupdf
import webbrowser
import json
import os
import sqlite3
import re
import hashlib
from datetime import datetime
from collections import Counter

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def cargar_skills():
    try:
        with open('skills.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def cargar_perfiles():
    perfiles = {}
    try:
        with open('profiles.json', 'r', encoding='utf-8') as f:
            perfiles.update(json.load(f))
    except FileNotFoundError:
        pass
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
            fecha TEXT, portal TEXT, skill_buscada TEXT, url TEXT, 
            favorito INTEGER DEFAULT 0, fingerprint TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metricas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT, skill TEXT, portal TEXT, match_score INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def guardar_busqueda(portal, skill, url, fingerprint=None):
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO busquedas (fecha, portal, skill_buscada, url, fingerprint) VALUES (?, ?, ?, ?, ?)',
        (datetime.now().strftime('%Y-%m-%d %H:%M'), portal, skill, url, fingerprint)
    )
    conn.commit()
    conn.close()

def guardar_metrica(skill, portal, match_score):
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO metricas (fecha, skill, portal, match_score) VALUES (?, ?, ?, ?)',
        (datetime.now().strftime('%Y-%m-%d'), skill, portal, match_score)
    )
    conn.commit()
    conn.close()

def obtener_historial():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fecha, portal, skill_buscada, url, favorito FROM busquedas ORDER BY id DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()
    return rows

def obtener_metricas():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('SELECT skill, COUNT(*) FROM metricas GROUP BY skill ORDER BY COUNT(*) DESC LIMIT 10')
    skills = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM busquedas')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(DISTINCT fingerprint) FROM busquedas')
    duplicados = total - cursor.fetchone()[0]
    conn.close()
    return {'skills': skills, 'total_busquedas': total, 'duplicados': duplicados}

def limpiar_historial():
    conn = sqlite3.connect('historial.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM busquedas')
    cursor.execute('DELETE FROM metricas')
    conn.commit()
    conn.close()

def calcular_fingerprint(empresa, titulo, ubicacion):
    texto = f"{empresa.lower()}{titulo.lower()}{ubicacion.lower()}"
    return hashlib.md5(texto.encode()).hexdigest()

SKILL_ALIASES = cargar_skills()
PERFILES = cargar_perfiles()

class PortalAdapter:
    def __init__(self, nombre, base_url, query_patterns=None):
        self.nombre = nombre
        self.base_url = base_url
        self.query_patterns = query_patterns or ["{}"]
    
    def build_search_url(self, skill, seniority="", location="Argentina"):
        for pattern in self.query_patterns:
            url = pattern.format(skill=skill, seniority=seniority, location=location)
            if url:
                return url
        return self.base_url.format(skill)

PORTALES = {
    "LinkedIn": PortalAdapter("LinkedIn", 
        "https://www.linkedin.com/jobs/search/?keywords={}&location=Argentina&f_WT=2",
        [
            "https://www.linkedin.com/jobs/search/?keywords={skill}&location=Argentina&f_WT=2",
            "https://www.linkedin.com/jobs/search/?keywords={skill}%20{seniority}&location=Argentina&f_WT=2"
        ]),
    "Indeed": PortalAdapter("Indeed",
        "https://ar.indeed.com/jobs?q={}&l=Argentina",
        ["https://ar.indeed.com/jobs?q={skill}&l=Argentina"]),
    "Computrabajo": PortalAdapter("Computrabajo",
        "https://www.computrabajo.com.ar/empleos-de-{}",
        ["https://www.computrabajo.com.ar/empleos-de-{skill}"]),
    "Bumeran": PortalAdapter("Bumeran",
        "https://www.bumeran.com.ar/empleos-busqueda-{}.html",
        ["https://www.bumeran.com.ar/empleos-busqueda-{skill}.html"])
}

class HistorialWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Historial de Búsquedas")
        self.geometry("900x600")
        self.grab_set()
        
        # Frame header
        frame_header = ctk.CTkFrame(self)
        frame_header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(frame_header, text="Historial de Búsquedas", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)
        
        self.btn_limpiar = ctk.CTkButton(frame_header, text="Limpiar Historial", command=self.limpiar_historial, 
                                        width=150, height=30, fg_color="#dc3545", hover_color="#c82333")
        self.btn_limpiar.pack(side="right", padx=10)
        
        # Frame para Treeview con scroll
        frame_tree = tk.Frame(self, bg="#1e1e1e")
        frame_tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(frame_tree, columns=("fecha", "portal", "skill", "url"), show="headings", height=20)
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("portal", text="Portal")
        self.tree.heading("skill", text="Skill")
        self.tree.heading("url", text="URL")
        
        self.tree.column("fecha", width=130, minwidth=100)
        self.tree.column("portal", width=100, minwidth=80)
        self.tree.column("skill", width=150, minwidth=100)
        self.tree.column("url", width=500, minwidth=200)
        
        scrollbar_y = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        frame_tree.grid_rowconfigure(0, weight=1)
        frame_tree.grid_columnconfigure(0, weight=1)
        
        self.cargar_historial()
    
    def cargar_historial(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        historial = obtener_historial()
        for row in historial:
            fecha, portal, skill, url, favorito = row
            self.tree.insert("", "end", values=(fecha, portal, skill, url))
    
    def limpiar_historial(self):
        if messagebox.askyesno("Confirmar", "¿Seguro que querés borrar todo el historial?"):
            limpiar_historial()
            self.cargar_historial()

class PalaFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pala Finder 3000 - RAM Mode: LOW")
        self.geometry("900x850")
        self.cv_path = ""
        self.cv_skills = set()
        self.cv_years = 0
        self.cv_modality = "Cualquiera"
        self.pestanas_abiertas = 0
        self.max_pestanas = 4
        init_db()
        self.crear_interfaz()
        
    def crear_interfaz(self):
        self.label_titulo = ctk.CTkLabel(self, text="Pala Finder 3000", font=ctk.CTkFont(size=28, weight="bold"))
        self.label_titulo.pack(pady=10)
        
        # Frame CV
        frame_cv = ctk.CTkFrame(self)
        frame_cv.pack(pady=10, padx=20, fill="x")
        
        self.btn_seleccionar = ctk.CTkButton(frame_cv, text="Seleccionar CV (PDF)", command=self.seleccionar_cv, width=200, height=35)
        self.btn_seleccionar.grid(row=0, column=0, padx=10, pady=10)
        
        self.label_estado = ctk.CTkLabel(frame_cv, text="Ningún archivo seleccionado", text_color="gray")
        self.label_estado.grid(row=0, column=1, padx=10, pady=10)
        
        # Perfil
        if PERFILES:
            frame_perfil = ctk.CTkFrame(self)
            frame_perfil.pack(pady=10, padx=20, fill="x")
            
            ctk.CTkLabel(frame_perfil, text="Perfil objetivo:").grid(row=0, column=0, padx=10, pady=10)
            self.combo_perfil = ctk.CTkComboBox(frame_perfil, values=list(PERFILES.keys()), command=self.calcular_match)
            self.combo_perfil.set("Seleccionar perfil...")
            self.combo_perfil.grid(row=0, column=1, padx=10, pady=10)
            
            self.btn_crear_perfil = ctk.CTkButton(frame_perfil, text="Crear Perfil", command=self.crear_perfil, width=120, height=30)
            self.btn_crear_perfil.grid(row=0, column=2, padx=10, pady=10)
        
        # Skills
        self.label_instruccion = ctk.CTkLabel(self, text="Skills detectadas (editables):", font=ctk.CTkFont(size=14))
        self.label_instruccion.pack(pady=5)
        
        self.text_skills = ctk.CTkTextbox(self, width=750, height=80)
        self.text_skills.pack(pady=5)
        self.text_skills.insert("0.0", "Cargá un CV para auto-detectar las skills...")
        self.text_skills.configure(state="disabled")
        
        # Match Score y Skill Gap
        self.frame_match = ctk.CTkFrame(self)
        self.frame_match.pack(pady=10, padx=20, fill="x")
        
        self.label_match_score = ctk.CTkLabel(self.frame_match, text="Match Score: --%", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_match_score.pack(pady=5)
        
        self.label_match_details = ctk.CTkLabel(self.frame_match, text="", justify="left")
        self.label_match_details.pack(pady=5)
        
        self.label_skill_gap = ctk.CTkLabel(self.frame_match, text="", justify="left", text_color="#f39c12")
        self.label_skill_gap.pack(pady=5)
        
        # Configuración
        frame_config = ctk.CTkFrame(self)
        frame_config.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(frame_config, text="Máximo de pestañas (RAM Mode):").grid(row=0, column=0, padx=10, pady=5)
        self.limit_tabs = ctk.CTkComboBox(frame_config, values=["2", "3", "4", "5", "6"], command=self.actualizar_ram_mode)
        self.limit_tabs.set("4")
        self.limit_tabs.grid(row=0, column=1, padx=10, pady=5)
        
        self.label_ram_mode = ctk.CTkLabel(frame_config, text="🟢 RAM Mode: LOW", text_color="#28a745")
        self.label_ram_mode.grid(row=0, column=2, padx=10, pady=5)
        
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
        
        # Dashboard de Métricas
        self.frame_metricas = ctk.CTkFrame(self)
        self.frame_metricas.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.frame_metricas, text="📊 Dashboard de Métricas", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        self.label_metricas = ctk.CTkLabel(self.frame_metricas, text="Cargá el CV y empezá a buscar para ver métricas", justify="left")
        self.label_metricas.pack(pady=5)
        
        # Botón Ver Historial
        self.btn_historial = ctk.CTkButton(self, text="📋 Ver Historial de Búsquedas", command=self.abrir_historial, 
                                          width=250, height=35, fg_color="#3498db", hover_color="#2980b9")
        self.btn_historial.pack(pady=10)
        
    def abrir_historial(self):
        ventana = HistorialWindow(self)
    
    def actualizar_ram_mode(self, event=None):
        self.max_pestanas = int(self.limit_tabs.get())
        if self.max_pestanas <= 3:
            self.label_ram_mode.configure(text="🟢 RAM Mode: LOW", text_color="#28a745")
        elif self.max_pestanas <= 5:
            self.label_ram_mode.configure(text="🟡 RAM Mode: MEDIUM", text_color="#f39c12")
        else:
            self.label_ram_mode.configure(text="🔴 RAM Mode: HIGH", text_color="#dc3545")
        
    def crear_perfil(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Crear Perfil Personalizado")
        ventana.geometry("600x600")
        ventana.grab_set()
        
        ctk.CTkLabel(ventana, text="Nombre del Perfil:", font=ctk.CTkFont(size=14)).pack(pady=10)
        entry_nombre = ctk.CTkEntry(ventana, width=400, placeholder_text="Ej: Contador Senior")
        entry_nombre.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Skills Requeridas (separadas por coma):", font=ctk.CTkFont(size=12)).pack(pady=10)
        text_requeridas = ctk.CTkTextbox(ventana, width=500, height=60)
        text_requeridas.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Skills Deseables (separadas por coma):", font=ctk.CTkFont(size=12)).pack(pady=10)
        text_deseables = ctk.CTkTextbox(ventana, width=500, height=60)
        text_deseables.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Seniority (Junior/Mid/Senior):", font=ctk.CTkFont(size=12)).pack(pady=10)
        combo_seniority = ctk.CTkComboBox(ventana, values=["Junior", "Mid", "Senior"])
        combo_seniority.set("Junior")
        combo_seniority.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Modalidad (Remoto/Hibrido/Presencial):", font=ctk.CTkFont(size=12)).pack(pady=10)
        combo_modality = ctk.CTkComboBox(ventana, values=["Remoto", "Hibrido", "Presencial", "Cualquiera"])
        combo_modality.set("Remoto")
        combo_modality.pack(pady=5)
        
        ctk.CTkLabel(ventana, text="Excluir (separadas por coma):", font=ctk.CTkFont(size=12)).pack(pady=10)
        text_exclude = ctk.CTkTextbox(ventana, width=500, height=60)
        text_exclude.pack(pady=5)
        text_exclude.insert("0.0", "senior, lead, manager, 5 años")
        
        def guardar():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showwarning("Error", "El nombre del perfil es obligatorio")
                return
            
            skills_req = [s.strip() for s in text_requeridas.get("0.0", "end").split(",") if s.strip()]
            skills_des = [s.strip() for s in text_deseables.get("0.0", "end").split(",") if s.strip()]
            exclude = [s.strip() for s in text_exclude.get("0.0", "end").split(",") if s.strip()]
            
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
                "seniority": combo_seniority.get(),
                "modality": combo_modality.get(),
                "exclude_keywords": exclude
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
            doc = pymupdf.open(self.cv_path)
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
            
            years_matches = re.findall(r'(\d+)\s*(años|years|anos)', texto)
            self.cv_years = max([int(y[0]) for y in years_matches]) if years_matches else 0
            
            self.cv_modality = "Cualquiera"
            if "remoto" in texto or "remote" in texto: self.cv_modality = "Remoto"
            elif "hibrido" in texto or "hybrid" in texto: self.cv_modality = "Hibrido"
            elif "presencial" in texto or "onsite" in texto: self.cv_modality = "Presencial"
            
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
        perfil_seniority = perfil.get("seniority", "Junior")
        perfil_modality = perfil.get("modality", "Cualquiera")
        exclude_keywords = perfil.get("exclude_keywords", [])
        
        skills_encontradas_req = skills_requeridas.intersection(self.cv_skills)
        skills_encontradas_des = skills_deseables.intersection(self.cv_skills)
        score_skills = (len(skills_encontradas_req) / len(skills_requeridas) * 0.6) if skills_requeridas else 0
        score_skills += (len(skills_encontradas_des) / len(skills_deseables) * 0.2) if skills_deseables else 0
        
        score_seniority = 0
        seniority_ranges = {"Junior": (0, 2), "Mid": (2, 5), "Senior": (5, 99)}
        if perfil_seniority in seniority_ranges:
            min_y, max_y = seniority_ranges[perfil_seniority]
            if min_y <= self.cv_years <= max_y:
                score_seniority = 0.2
            elif abs(self.cv_years - min_y) <= 1:
                score_seniority = 0.1
        
        score_modality = 0.2 if perfil_modality == "Cualquiera" or perfil_modality == self.cv_modality else 0.0
        
        match_percentage = int((score_skills + score_seniority + score_modality) * 100)
        
        self.label_match_score.configure(text=f"Match Score: {match_percentage}%")
        
        details = f"✓ Skills: {', '.join(sorted(skills_encontradas_req)) if skills_encontradas_req else 'Ninguna'}\n"
        details += f"✗ Faltan: {', '.join(sorted(skills_requeridas - self.cv_skills)) if skills_requeridas - self.cv_skills else 'Ninguna'}\n"
        details += f"📅 Experiencia: {self.cv_years} años (Perfil: {perfil_seniority})\n"
        details += f"🏠 Modalidad: {self.cv_modality} (Perfil: {perfil_modality})"
        if exclude_keywords:
            details += f"\n🚫 Excluye: {', '.join(exclude_keywords[:3])}"
        self.label_match_details.configure(text=details)
        
        skills_faltantes = list(skills_requeridas - self.cv_skills)
        if skills_faltantes:
            potential_score_skills = 0.8
            potential_total = int((potential_score_skills + score_seniority + score_modality) * 100)
            gap_text = f"🚀 Skill Gap: Si aprendés {', '.join(skills_faltantes[:3])}, subirías al {potential_total}%"
            self.label_skill_gap.configure(text=gap_text)
        else:
            self.label_skill_gap.configure(text=" ¡Tenés todas las skills requeridas!")

    def agregar_portal(self):
        nombre = self.entry_portal_name.get().strip()
        url = self.entry_portal_url.get().strip()
        
        if nombre and url and "{}" in url:
            PORTALES[nombre] = PortalAdapter(nombre, url)
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
        self.max_pestanas = int(self.limit_tabs.get())
        
        perfil_seleccionado = self.combo_perfil.get()
        exclude_keywords = []
        if perfil_seleccionado in PERFILES:
            exclude_keywords = PERFILES[perfil_seleccionado].get("exclude_keywords", [])
        
        total_abiertas = 0
        skills_filtradas = []
        
        for skill in skills_a_buscar:
            if any(exclude.lower() in skill.lower() for exclude in exclude_keywords):
                continue
            skills_filtradas.append(skill)
        
        for skill in skills_filtradas:
            if total_abiertas >= self.max_pestanas:
                break
            skill_url = skill.replace(" ", "+")
            
            for portal_name, portal_adapter in PORTALES.items():
                if total_abiertas >= self.max_pestanas:
                    break
                url_final = portal_adapter.build_search_url(skill, location="Argentina")
                webbrowser.open(url_final)
                
                fingerprint = calcular_fingerprint(portal_name, skill, "Argentina")
                guardar_busqueda(portal_name, skill, url_final, fingerprint)
                guardar_metrica(skill, portal_name, 0)
                
                total_abiertas += 1
        
        self.pestanas_abiertas = total_abiertas
        messagebox.showinfo("Listo bo", f"Se abrieron {total_abiertas} pestañas (RAM Mode: {self.max_pestanas}). A aplicar.")

if __name__ == "__main__":
    app = PalaFinderApp()
    app.mainloop()