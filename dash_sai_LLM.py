#ADOPCION

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import re
import requests
import json
import os

# Configuración de la página
st.set_page_config(
    page_title="Dashboard IA Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# FUNCIÓN OPTIMIZADA: PROCESAMIENTO DE ARCHIVOS DE ENTRADA (SIN INTERFAZ)
# ==========================================

@st.cache_data
def process_input_files():
    """
    Procesa automáticamente dos archivos de entrada y los convierte en el formato requerido
    para el dashboard de adopción SAI.
    
    Busca automáticamente los archivos en el directorio actual:
    - areas_personas.xlsx: Datos de usuarios (debe contener columnas: NOMBRE, PAIS, CARGO, AREA)
    - uso_por_mes.xlsx: Datos de uso mensual (debe contener NOMBRE y columnas de meses)
    
    Returns:
        tuple: (df_original, df_melted, month_columns_sorted) o (None, None, None) si hay error
    """
    try:
        # Archivos fijos predefinidos
        current_dir = os.getcwd()
        file_areas_personas = os.path.join(current_dir, 'areas_personas.xlsx')
        file_uso_por_mes = os.path.join(current_dir, 'uso_por_mes.xlsx')
        
        # Verificar que ambos archivos existan
        if not os.path.exists(file_areas_personas):
            st.error(f"❌ No se encontró el archivo: areas_personas.xlsx")
            return None, None, None
            
        if not os.path.exists(file_uso_por_mes):
            st.error(f"❌ No se encontró el archivo: uso_por_mes.xlsx")
            return None, None, None
        
        # Cargar archivos automáticamente
        df_users = pd.read_excel(file_areas_personas)
        
        # Cargar archivo de uso y eliminar la segunda fila (índice 1)
        df_usage = pd.read_excel(file_uso_por_mes)
        df_usage = df_usage.drop('Total', axis=1)
        if len(df_usage) > 1:
            df_usage = df_usage.drop(df_usage.index[1]).reset_index(drop=True)
        
        # Validar columnas requeridas en archivo de usuarios
        df_usage.rename(columns={'Custom Date': 'NOMBRE'}, inplace=True) 
        required_user_columns = ['NOMBRE', 'PAIS', 'CARGO', 'AREA']
        missing_user_cols = [col for col in required_user_columns if col not in df_users.columns]
        
        if missing_user_cols:
            st.error(f"❌ Faltan columnas en areas_personas.xlsx: {missing_user_cols}")
            st.info(f"📋 Columnas disponibles: {list(df_users.columns)}")
            return None, None, None
        
        # Validar que archivo de uso tenga columna NOMBRE
        if 'NOMBRE' not in df_usage.columns:
            st.error(f"❌ Falta columna 'NOMBRE' en uso_por_mes.xlsx")
            st.info(f"📋 Columnas disponibles: {list(df_usage.columns)}")
            return None, None, None
        
        # OPTIMIZACIÓN: Normalizar nombres eliminando espacios extras y convirtiendo a mayúsculas
        # Guardar nombres originales para mantenerlos en el resultado final
        df_users['NOMBRE_ORIGINAL'] = df_users['NOMBRE']
        df_usage['NOMBRE_ORIGINAL'] = df_usage['NOMBRE']
        
        # Función para normalizar nombres: elimina espacios múltiples y espacios al inicio/final
        def normalize_name(name):
            """Normaliza un nombre eliminando espacios extras y convirtiendo a mayúsculas"""
            if pd.isna(name):
                return ''
            # Convertir a string, eliminar espacios al inicio/final y reemplazar múltiples espacios por uno solo
            return ' '.join(str(name).strip().split()).upper()
        
        # Aplicar normalización a ambos dataframes
        df_users['NOMBRE_NORMALIZADO'] = df_users['NOMBRE'].apply(normalize_name)
        df_usage['NOMBRE_NORMALIZADO'] = df_usage['NOMBRE'].apply(normalize_name)
        
        # Identificar columnas de meses en archivo de uso
        month_columns = [col for col in df_usage.columns if col not in ['NOMBRE', 'NOMBRE_ORIGINAL', 'NOMBRE_NORMALIZADO']]
        
        if not month_columns:
            st.error(f"❌ No se encontraron columnas de meses en uso_por_mes.xlsx")
            return None, None, None
        
        # Realizar merge usando nombres normalizados
        df_merged = pd.merge(
            df_users, 
            df_usage, 
            on='NOMBRE_NORMALIZADO', 
            how='inner',
            suffixes=('_users', '_usage')
        )
        
        if len(df_merged) == 0:
            st.error("❌ No se encontraron coincidencias entre los archivos. Verifica que los nombres coincidan.")
            # Mostrar algunos ejemplos de nombres para debugging
            st.info("📋 Ejemplos de nombres en areas_personas.xlsx (normalizados):")
            st.text(df_users['NOMBRE_NORMALIZADO'].head(10).tolist())
            st.info("📋 Ejemplos de nombres en uso_por_mes.xlsx (normalizados):")
            st.text(df_usage['NOMBRE_NORMALIZADO'].head(10).tolist())
            return None, None, None
        
        # Usar el nombre original del archivo de usuarios como nombre principal
        df_merged['NOMBRE'] = df_merged['NOMBRE_ORIGINAL_users']
        
        # Eliminar columnas auxiliares que ya no necesitamos
        columns_to_drop = ['NOMBRE_NORMALIZADO', 'NOMBRE_ORIGINAL_users', 'NOMBRE_ORIGINAL_usage']
        df_merged = df_merged.drop(columns=columns_to_drop, errors='ignore')
        
        # Limpiar valores nulos en las columnas básicas
        df_merged['NOMBRE'] = df_merged['NOMBRE'].fillna('Sin Nombre')
        df_merged['PAIS'] = df_merged['PAIS'].fillna('Sin País')
        df_merged['CARGO'] = df_merged['CARGO'].fillna('Sin Cargo')
        df_merged['AREA'] = df_merged['AREA'].fillna('Sin Área')

        # FILTRAR: Excluir área de "Operaciones"
        df_merged = df_merged[df_merged['AREA'].str.lower() != 'operaciones']

        # Ordenar meses cronológicamente
        month_columns_sorted = sort_months_chronologically(month_columns)

        # Convertir datos a formato long para mejor análisis
        basic_columns = ['NOMBRE', 'PAIS', 'CARGO', 'AREA']
        df_melted = pd.melt(
            df_merged,
            id_vars=basic_columns,
            value_vars=month_columns,
            var_name='Mes',
            value_name='usos_ia'
        )

        # Limpiar datos nulos en usos de IA
        df_melted['usos_ia'] = pd.to_numeric(df_melted['usos_ia'], errors='coerce').fillna(0)
        
        return df_merged, df_melted, month_columns_sorted
        
    except Exception as e:
        st.error(f"❌ Error al procesar los archivos: {str(e)}")
        st.info("💡 Verifica que los archivos tengan el formato correcto y las columnas requeridas")
        return None, None, None

# ==========================================
# FUNCIONES EXISTENTES (SIN CAMBIOS)
# ==========================================

# FUNCIÓN: Llamada al LLM para generar resumen ejecutivo
def generate_llm_summary(data_text, api_key):
    """
    Genera un resumen ejecutivo usando el LLM a través de la API proporcionada
    
    Args:
        data_text: Texto plano con toda la información visible
        api_key: Clave de API para el servicio
    
    Returns:
        str: Resumen generado por el LLM o mensaje de error
    """
    try:
        url = "https://sai-library.saiapplications.com"
        headers = {"X-Api-Key": api_key}
        data = {
            "inputs": {
                "data": data_text,
            }
        }
        
        response = requests.post(f"{url}/api/templates/6892acca9315b2d72e0e9ab4/execute", json=data, headers=headers)
        
        if response.status_code == 200:
            return response.text
        else:
            return f"Error en la API: Código de estado {response.status_code}"
            
    except Exception as e:
        return f"Error al conectar con el LLM: {str(e)}"

# FUNCIÓN NUEVA: Llamada al LLM para responder preguntas específicas del usuario
def generate_llm_question_response(data_text, pregunta, api_key):
    """
    Genera respuesta a pregunta específica del usuario usando el LLM a través de la API proporcionada
    
    Args:
        data_text: Texto plano con toda la información visible (variable 'data')
        pregunta: Pregunta específica del usuario (variable 'pregunta')
        api_key: Clave de API para el servicio
    
    Returns:
        str: Respuesta generada por el LLM o mensaje de error
    """
    try:
        url = "https://sai-library.saiapplications.com"
        headers = {"X-Api-Key": api_key}
        data = {
            "inputs": {
                "data": data_text,
                "pregunta": pregunta
            }
        }
        
        response = requests.post(f"{url}/api/templates/68942f6f8c7cd1b38cbd12e6/execute", json=data, headers=headers)
        
        if response.status_code == 200:
            return response.text
        else:
            return f"Error en la API: Código de estado {response.status_code}"
            
    except Exception as e:
        return f"Error al conectar con el LLM: {str(e)}"

# FUNCIÓN: Llamada al LLM para generar insights del dashboard
def generate_llm_insights(data_text, api_key):
    """
    Genera insights del dashboard usando el LLM a través de la API proporcionada
    
    Args:
        data_text: Texto plano con toda la información visible
        api_key: Clave de API para el servicio
    
    Returns:
        str: Insights generados por el LLM o mensaje de error
    """
    try:
        url = "https://sai-library.saiapplications.com"
        headers = {"X-Api-Key": api_key}
        data = {
            "inputs": {
                "data": data_text,
            }
        }
        
        # Usar un endpoint diferente para insights (asumiendo que existe)
        response = requests.post(f"{url}/api/templates/6892acca9315b2d72e0e9ab4/execute", json=data, headers=headers)
        
        if response.status_code == 200:
            return response.text
        else:
            return f"Error en la API: Código de estado {response.status_code}"
            
    except Exception as e:
        return f"Error al conectar con el LLM: {str(e)}"

# FUNCIÓN: Generar texto plano con toda la información visible
def generate_summary_text(filtered_data, selected_months, selected_countries, selected_areas, filter_type):
    """
    Genera un texto plano con toda la información visible basada en los filtros seleccionados
    
    Args:
        filtered_data: DataFrame con datos filtrados
        selected_months: Lista de meses seleccionados
        selected_countries: Lista de países seleccionados
        selected_areas: Lista de áreas seleccionadas
        filter_type: Tipo de filtro temporal aplicado
    
    Returns:
        str: Texto plano con toda la información para el LLM
    """
    
    # Encabezado del resumen
    summary_text = "=== RESUMEN EJECUTIVO - DASHBOARD DE ANÁLISIS SAI ===\n\n"
    
    # Información de filtros aplicados
    summary_text += "FILTROS APLICADOS:\n"
    summary_text += f"- Tipo de filtro temporal: {filter_type}\n"
    summary_text += f"- Meses seleccionados ({len(selected_months)}): {', '.join(selected_months)}\n"
    summary_text += f"- Países seleccionados ({len(selected_countries)}): {', '.join(selected_countries)}\n"
    summary_text += f"- Áreas seleccionadas ({len(selected_areas)}): {', '.join(selected_areas)}\n\n"
    
    # Métricas principales
    summary_text += "MÉTRICAS PRINCIPALES:\n"
    
    # Total Profesionales Elegibles
    total_eligible_professionals = filtered_data['NOMBRE'].nunique()
    summary_text += f"- Total Profesionales Elegibles: {total_eligible_professionals}\n"
    
    # Total de Usuarios Activos
    active_users = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
    summary_text += f"- Total Usuarios Activos: {active_users}\n"
    
    # % Acumulado Adopción SAI
    users_with_usage = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
    total_unique_users = filtered_data['NOMBRE'].nunique()
    if total_unique_users > 0:
        cumulative_adoption_rate = (users_with_usage / total_unique_users) * 100
    else:
        cumulative_adoption_rate = 0
    summary_text += f"- % Acumulado Adopción SAI: {cumulative_adoption_rate:.1f}%\n"
    
    # % Promedio Adopción SAI
    monthly_adoption_rates = []
    for month in selected_months:
        month_data = filtered_data[filtered_data['Mes'] == month]
        total_users_month = month_data['NOMBRE'].nunique()
        active_users_month = month_data[month_data['usos_ia'] > 0]['NOMBRE'].nunique()
        if total_users_month > 0:
            monthly_rate = (active_users_month / total_users_month) * 100
            monthly_adoption_rates.append(monthly_rate)
    
    if monthly_adoption_rates:
        average_adoption_rate = sum(monthly_adoption_rates) / len(monthly_adoption_rates)
    else:
        average_adoption_rate = 0
    summary_text += f"- % Promedio Adopción SAI: {average_adoption_rate:.1f}%\n\n"
    
    # Análisis de adopción por mes
    summary_text += "ANÁLISIS DE ADOPCIÓN POR MES:\n"
    for month in selected_months:
        month_data = filtered_data[filtered_data['Mes'] == month]
        total_users = month_data['NOMBRE'].nunique()
        users_with_usage = month_data[month_data['usos_ia'] > 0]['NOMBRE'].nunique()
        users_without_usage = total_users - users_with_usage
        adoption_percentage = (users_with_usage / total_users) * 100 if total_users > 0 else 0
        
        summary_text += f"- {month}: {total_users} usuarios totales, {users_with_usage} activos, {users_without_usage} inactivos, {adoption_percentage:.1f}% adopción\n"
    
    summary_text += "\n"
    
    # Análisis por país
    summary_text += "ANÁLISIS POR PAÍS:\n"
    country_data = filtered_data.groupby('PAIS').agg({
        'NOMBRE': 'nunique'
    }).reset_index()
    
    for _, row in country_data.iterrows():
        country = row['PAIS']
        users = row['NOMBRE']
        
        # Calcular adopción por país
        country_filtered = filtered_data[filtered_data['PAIS'] == country]
        active_users_country = country_filtered[country_filtered['usos_ia'] > 0]['NOMBRE'].nunique()
        adoption_rate = (active_users_country / users) * 100 if users > 0 else 0
        
        summary_text += f"- {country}: {users} usuarios, {adoption_rate:.1f}% adopción\n"
    
    summary_text += "\n"
    
    # Estadísticas adicionales
    summary_text += "ESTADÍSTICAS ADICIONALES:\n"
    summary_text += f"- Total de registros analizados: {len(filtered_data)}\n"
    summary_text += f"- Usuarios únicos: {filtered_data['NOMBRE'].nunique()}\n"
    summary_text += f"- Países únicos: {filtered_data['PAIS'].nunique()}\n"
    summary_text += f"- Áreas únicas: {filtered_data['AREA'].nunique()}\n"
    summary_text += f"- Cargos únicos: {filtered_data['CARGO'].nunique()}\n"
    summary_text += f"- Meses analizados: {len(selected_months)}\n"
    
    return summary_text

# FUNCIÓN: Validar condiciones para mostrar gráficos
def validate_chart_conditions(selected_months, selected_countries, selected_areas):
    """
    Valida las condiciones necesarias para mostrar cada tipo de gráfico
    
    Args:
        selected_months: Lista de meses seleccionados
        selected_countries: Lista de países seleccionados
        selected_areas: Lista de áreas seleccionadas
    
    Returns:
        dict: Diccionario con las validaciones para cada gráfico
    """
    return {
        'show_adoption_trend': len(selected_months) > 1,
        'show_adoption_by_country': len(selected_countries) > 1,
        'show_adoption_heatmap': len(selected_countries) > 1 and len(selected_areas) > 1
    }

# FUNCIÓN: Mostrar mensaje informativo cuando no se cumplen condiciones
def show_chart_requirement_message(chart_type, requirement):
    """
    Muestra un mensaje informativo cuando no se cumplen las condiciones para mostrar un gráfico
    
    Args:
        chart_type: Tipo de gráfico
        requirement: Requisito no cumplido
    """
    messages = {
        'multiple_months': "📅 **Se requieren al menos 2 meses** para mostrar la evolución temporal.",
        'multiple_countries': "🌍 **Se requieren al menos 2 países** para mostrar la comparación entre países.",
        'multiple_dimensions': "🔥 **Se requieren al menos 2 países y 2 áreas** para generar el mapa de calor."
    }
    
    st.info(messages.get(requirement, "ℹ️ Condiciones insuficientes para mostrar este gráfico."))

# FUNCIÓN: Formatear listas para mostrar en descripciones
def format_list_for_description(items, max_items=None, item_type="elementos"):
    """
    Formatea una lista de elementos para mostrar en descripciones de manera legible
    MODIFICADO: Ahora muestra TODOS los elementos sin límite
    
    Args:
        items: Lista de elementos a formatear
        max_items: Parámetro mantenido por compatibilidad pero no se usa
        item_type: Tipo de elementos (para el texto de resumen)
    
    Returns:
        str: Texto formateado para la descripción con TODOS los elementos
    """
    if not items:
        return f"ningún {item_type}"
    
    if len(items) == 1:
        return f"**{items[0]}**"
    elif len(items) == 2:
        return f"**{items[0]}** y **{items[1]}**"
    else:
        # CAMBIO PRINCIPAL: Mostrar TODOS los elementos sin límite
        return f"**{', '.join(items[:-1])}** y **{items[-1]}**"

# FUNCIÓN: Formatear período temporal para descripciones
def format_time_period_for_description(selected_months):
    """
    Formatea el período temporal para mostrar en descripciones de manera legible
    
    Args:
        selected_months: Lista de meses seleccionados
    
    Returns:
        str: Texto formateado del período temporal
    """
    if not selected_months:
        return "ningún período"
    
    if len(selected_months) == 1:
        return f"**{selected_months[0]}**"
    elif len(selected_months) <= 3:
        return f"**{len(selected_months)} meses** ({', '.join(selected_months)})"
    else:
        # Ordenar meses cronológicamente para mostrar rango
        sorted_months = sort_months_chronologically(selected_months)
        return f"**{len(selected_months)} meses** (desde **{sorted_months[0]}** hasta **{sorted_months[-1]}**)"

# FUNCIÓN: Generar descripción dinámica para gráficos
def generate_chart_description(chart_type, selected_months, selected_countries, selected_areas):
    """
    Genera una descripción dinámica detallada para cada gráfico basada en los filtros seleccionados
    con formato mejorado y texto más natural
    MODIFICADO: Ahora muestra TODOS los países y áreas seleccionados
    
    Args:
        chart_type: Tipo de gráfico ('trend', 'country', 'heatmap')
        selected_months: Lista de meses seleccionados
        selected_countries: Lista de países seleccionados
        selected_areas: Lista de áreas seleccionadas
    
    Returns:
        str: Descripción detallada y dinámica del gráfico
    """
    # Formatear elementos para las descripciones - SIN LÍMITE DE ELEMENTOS
    months_text = format_time_period_for_description(selected_months)
    countries_text = format_list_for_description(selected_countries, item_type="países")
    areas_text = format_list_for_description(selected_areas, item_type="áreas")
    
    # Generar descripciones específicas por tipo de gráfico
    if chart_type == 'trend':
        return (f"📈 **Análisis temporal de adopción SAI:** Este gráfico muestra la evolución del "
                f"porcentaje de adopción durante {months_text}, evaluando los países {countries_text} "
                f"en las áreas de {areas_text}. La línea de tendencia indica la dirección general "
                f"del crecimiento o decrecimiento en la adopción de la herramienta SAI.")
    
    elif chart_type == 'country':
        return (f"🌍 **Comparación de adopción por países:** Este gráfico compara el porcentaje de "
                f"adopción de SAI entre {countries_text} durante el período {months_text}, "
                f"analizando específicamente las áreas de {areas_text}. Los países están ordenados "
                f"de mayor a menor adopción para facilitar la identificación de líderes en la "
                f"implementación de SAI.")
    
    elif chart_type == 'heatmap':
        return (f"🔥 **Mapa de calor multidimensional:** Esta visualización muestra la intensidad "
                f"de adopción de SAI cruzando {countries_text} con {areas_text} durante el período "
                f"{months_text}. Los colores más intensos (verdes) indican mayor adopción, mientras "
                f"que los colores más fríos (rojos) representan menor adopción, permitiendo "
                f"identificar combinaciones país-área con mejor performance.")
    
    return "Descripción no disponible para este tipo de gráfico."

# Función para ordenar meses cronológicamente
def sort_months_chronologically(month_columns):
    """
    Ordena los meses de forma cronológica (2024 primero, luego 2025)
    """
    def extract_month_year(month_str):
        # Extraer mes y año del formato "Mes-Año" (ej: "Sep-24", "Abril 2025")
        month_str = str(month_str).strip()
        
        # Mapeo de meses en español a números
        month_mapping = {
            'ene': 1, 'enero': 1, 'jan': 1,
            'feb': 2, 'febrero': 2, 'feb': 2,
            'mar': 3, 'marzo': 3, 'mar': 3,
            'abr': 4, 'abril': 4, 'apr': 4,
            'may': 5, 'mayo': 5, 'may': 5,
            'jun': 6, 'junio': 6, 'jun': 6,
            'jul': 7, 'julio': 7, 'jul': 7,
            'ago': 8, 'agosto': 8, 'aug': 8,
            'sep': 9, 'septiembre': 9, 'sep': 9,
            'oct': 10, 'octubre': 10, 'oct': 10,
            'nov': 11, 'noviembre': 11, 'nov': 11,
            'dic': 12, 'diciembre': 12, 'dec': 12
        }
        
        # Buscar patrones comunes de fecha
        patterns = [
            r'(\w+)[-\s](\d{2,4})',  # Sep-24, Abril 2025
            r'(\w+)\s+(\d{2,4})',    # Sep 24, Abril 2025
            r'(\d{1,2})[-/](\d{2,4})', # 9-24, 04/2025
        ]
        
        for pattern in patterns:
            match = re.search(pattern, month_str, re.IGNORECASE)
            if match:
                month_part = match.group(1).lower()
                year_part = match.group(2)
                
                # Convertir año de 2 dígitos a 4 dígitos
                if len(year_part) == 2:
                    year_num = int(year_part)
                    if year_num >= 24:  # Asumiendo que 24+ es 2024+
                        year_part = f"20{year_part}"
                    else:
                        year_part = f"20{year_part}"
                
                # Buscar el mes en el mapeo
                month_num = None
                for key, value in month_mapping.items():
                    if key in month_part:
                        month_num = value
                        break
                
                # Si no se encuentra el mes por nombre, intentar convertir directamente
                if month_num is None:
                    try:
                        month_num = int(month_part)
                    except:
                        month_num = 1  # Default
                
                return (int(year_part), month_num)
        
        # Si no se puede parsear, devolver valores por defecto
        return (2024, 1)
    
    # Crear lista de tuplas (mes_original, año, mes_num) para ordenar
    month_data = []
    for month in month_columns:
        year, month_num = extract_month_year(month)
        month_data.append((month, year, month_num))
    
    # Ordenar por año y luego por mes
    month_data.sort(key=lambda x: (x[1], x[2]))
    
    # Devolver solo los nombres de meses ordenados
    return [item[0] for item in month_data]

# FUNCIÓN: Filtrar meses por período (EXCLUYE MES ACTUAL)
def filter_months_by_period(month_columns_sorted, selected_period):
    """
    Filtra los meses según el período seleccionado, excluyendo el mes más reciente (mes en curso)
    para los filtros de "Últimos X meses"
    """
    if selected_period == "Todos los meses":
        return month_columns_sorted
    
    # OPTIMIZACIÓN: Para filtros de "Últimos X meses", excluir el mes más reciente
    if selected_period in ["Últimos 3 meses", "Últimos 6 meses", "Últimos 9 meses"]:
        # Excluir el último mes (mes en curso) para estos filtros
        available_months = month_columns_sorted[:-1] if len(month_columns_sorted) > 1 else []
        
        # Determinar cuántos meses tomar
        period_mapping = {
            "Últimos 3 meses": 3,
            "Últimos 6 meses": 6,
            "Últimos 9 meses": 9
        }
        
        num_months = period_mapping[selected_period]
        return available_months[-num_months:] if len(available_months) >= num_months else available_months
    
    # FUNCIONALIDAD EXISTENTE: Mes anterior
    if selected_period == "Mes anterior":
        # Retorna el penúltimo mes (mes anterior al último)
        if len(month_columns_sorted) >= 2:
            return [month_columns_sorted[-2]]  # Penúltimo mes
        elif len(month_columns_sorted) == 1:
            return [month_columns_sorted[0]]  # Si solo hay un mes, retorna ese
        else:
            return []  # Si no hay meses, retorna lista vacía
    
    return month_columns_sorted

# FUNCIÓN: Crear filtros dinámicos según la selección del usuario
def create_dynamic_filters(month_columns_sorted):
    """
    Crea filtros dinámicos basados en la selección del usuario (Período o Meses específicos)
    """
    # Selector principal: Filtrar por período o por meses específicos
    filter_type = st.sidebar.radio(
        "🎯 Tipo de Filtro Temporal",
        ["Por Período", "Por Meses Específicos"],
        help="Selecciona cómo quieres filtrar los datos temporalmente"
    )
    
    selected_months = []
    
    if filter_type == "Por Período":
        # Opciones de período predefinidas
        period_options = [
            "Todos los meses",
            "Mes anterior",
            "Últimos 3 meses", 
            "Últimos 6 meses",
            "Últimos 9 meses"
        ]
        
        selected_period = st.sidebar.selectbox(
            "📅 Seleccionar Período",
            period_options,
            help="Selecciona un período predefinido para filtrar los datos. Los filtros 'Últimos X meses' excluyen el mes más reciente."
        )
        
        # Filtrar meses según el período seleccionado
        selected_months = filter_months_by_period(month_columns_sorted, selected_period)
        
        # OPTIMIZACIÓN: Mostrar información detallada del período seleccionado
        if selected_period == "Mes anterior":
            if len(selected_months) > 0:
                st.sidebar.info(f"📊 **Período:** {selected_period}\n\n**Mes incluido:** {selected_months[0]}")
            else:
                st.sidebar.warning("⚠️ No hay suficientes meses para mostrar el mes anterior")
        elif selected_period in ["Últimos 3 meses", "Últimos 6 meses", "Últimos 9 meses"]:
            if len(selected_months) > 0:
                st.sidebar.info(f"📊 **Período:** {selected_period} (excluyendo mes actual)\n\n**Meses incluidos:** {len(selected_months)} meses\n\n**Rango:** {selected_months[0]} a {selected_months[-1]}")
            else:
                st.sidebar.warning(f"⚠️ No hay suficientes meses históricos para mostrar {selected_period}")
        elif selected_period == "Todos los meses":
            st.sidebar.info(f"📊 **Período:** Todos los meses disponibles\n\n**Total:** {len(selected_months)} meses")
    
    else:  # Por Meses Específicos
        # Permitir selección manual de meses
        selected_months = st.sidebar.multiselect(
            "📅 Seleccionar Meses Específicos",
            month_columns_sorted,
            default=month_columns_sorted,  # Por defecto todos los meses
            help="Selecciona manualmente los meses que deseas analizar"
        )
        
        # Mostrar información de la selección manual
        if selected_months:
            st.sidebar.info(f"📊 **Meses seleccionados:** {len(selected_months)} de {len(month_columns_sorted)} disponibles")
        else:
            st.sidebar.warning("⚠️ Selecciona al menos un mes para continuar")
    
    return selected_months, filter_type

# FUNCIÓN: Crear filtros múltiples con checkboxes (MODIFICADA - SIN FILTRO DE CARGO)
def create_multiple_filters(df_melted):
    """
    Crea filtros múltiples con checkboxes para países y áreas (sin filtro de cargo)
    
    Args:
        df_melted: DataFrame con los datos
    
    Returns:
        tuple: (selected_countries, selected_areas)
    """
    st.sidebar.subheader("🎯 Filtros Múltiples")
    
    # Filtro múltiple por países
    st.sidebar.write("🌍 **Seleccionar Países:**")
    countries = sorted([str(x) for x in df_melted['PAIS'].dropna().unique()])
    
    # Checkbox para seleccionar todos los países
    select_all_countries = st.sidebar.checkbox("Seleccionar todos los países", value=True)
    
    if select_all_countries:
        selected_countries = countries
    else:
        selected_countries = []
        for country in countries:
            if st.sidebar.checkbox(f"📍 {country}", key=f"country_{country}"):
                selected_countries.append(country)
    
    st.sidebar.markdown("---")
    
    # MODIFICADO: Filtrar áreas para excluir "Operaciones"
    st.sidebar.write("🏢 **Seleccionar Áreas:**")
    all_areas = sorted([str(x) for x in df_melted['AREA'].dropna().unique()])
    # Excluir "Operaciones" de las áreas disponibles
    areas = [area for area in all_areas if area.lower() != 'operaciones']
    
    # Checkbox para seleccionar todas las áreas (excepto Operaciones)
    select_all_areas = st.sidebar.checkbox("Seleccionar todas las áreas", value=True)
    
    if select_all_areas:
        selected_areas = areas
    else:
        selected_areas = []
        for area in areas:
            if st.sidebar.checkbox(f"🏢 {area}", key=f"area_{area}"):
                selected_areas.append(area)
    
    # Mostrar resumen de selección
    st.sidebar.markdown("---")
    st.sidebar.write("📊 **Resumen de Filtros:**")
    st.sidebar.write(f"• **Países:** {len(selected_countries)} seleccionados")
    st.sidebar.write(f"• **Áreas:** {len(selected_areas)} seleccionadas")
    
    return selected_countries, selected_areas

# FUNCIÓN: Crear métricas principales en 2 filas con métricas de adopción
def create_metrics(df_melted, filtered_data, selected_months):
    """
    Calcula y muestra métricas principales del dashboard organizadas en 2 filas de 2 columnas cada una
    Solo incluye métricas relacionadas con adopción
    """
    # PRIMERA FILA - 2 métricas principales
    col1, col2 = st.columns(2)

    with col1:
        # Total Profesionales Elegibles
        total_eligible_professionals = filtered_data['NOMBRE'].nunique()
        st.metric("👥 Total Profesionales Elegibles", total_eligible_professionals)

    with col2:
        # Total de Usuarios Activos (usuarios con al menos 1 uso de IA)
        active_users = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
        st.metric("🚀 Total Usuarios Activos", active_users)

    # SEGUNDA FILA - 2 métricas de adopción
    col3, col4 = st.columns(2)

    with col3:
        # % Acumulado Adopción SAI
        users_with_usage = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
        total_unique_users = filtered_data['NOMBRE'].nunique()
        
        if total_unique_users > 0:
            cumulative_adoption_rate = (users_with_usage / total_unique_users) * 100
        else:
            cumulative_adoption_rate = 0
            
        st.metric("🎯 % Acumulado Adopción SAI", f"{cumulative_adoption_rate:.1f}%")

    with col4:
        # % Promedio Adopción SAI
        # Calcula el promedio de adopción por mes seleccionado
        monthly_adoption_rates = []
        
        for month in selected_months:
            month_data = filtered_data[filtered_data['Mes'] == month]
            total_users_month = month_data['NOMBRE'].nunique()
            active_users_month = month_data[month_data['usos_ia'] > 0]['NOMBRE'].nunique()
            
            if total_users_month > 0:
                monthly_rate = (active_users_month / total_users_month) * 100
                monthly_adoption_rates.append(monthly_rate)
        
        # Calcular promedio de adopción mensual
        if monthly_adoption_rates:
            average_adoption_rate = sum(monthly_adoption_rates) / len(monthly_adoption_rates)
        else:
            average_adoption_rate = 0
            
        st.metric("📊 % Promedio Adopción SAI", f"{average_adoption_rate:.1f}%")

# FUNCIÓN: Gráfico de adopción SAI vs País con ejes fijos de 0 a 100%
def create_adoption_by_country(filtered_data):
    """
    Crea gráfico de % de adopción de SAI por país con ejes fijos de 0 a 100%
    """
    # Calcular adopción por país
    country_adoption = []
    
    for country in filtered_data['PAIS'].unique():
        country_data = filtered_data[filtered_data['PAIS'] == country]
        total_users = country_data['NOMBRE'].nunique()
        active_users = country_data[country_data['usos_ia'] > 0]['NOMBRE'].nunique()
        
        adoption_rate = (active_users / total_users) * 100 if total_users > 0 else 0
        
        country_adoption.append({
            'País': country,
            'Total_Usuarios': total_users,
            'Usuarios_Activos': active_users,
            'Porcentaje_Adopcion': adoption_rate
        })
    
    adoption_df = pd.DataFrame(country_adoption)
    adoption_df = adoption_df.sort_values('Porcentaje_Adopcion', ascending=False)
    
    # Crear gráfico de barras
    fig = px.bar(
        adoption_df,
        x='País',
        y='Porcentaje_Adopcion',
        title='🌎 % Adopción SAI por País',
        color='Porcentaje_Adopcion',
        color_continuous_scale='viridis',
        hover_data=['Total_Usuarios', 'Usuarios_Activos']
    )
    
    # EJES FIJOS DE 0 A 100%
    fig.update_layout(
        xaxis_title="País",
        yaxis_title="% Adopción SAI",
        yaxis=dict(range=[0, 100]),  # Eje Y fijo de 0 a 100%
        xaxis_tickangle=-45
    )
    
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>' +
                      'Adopción: %{y:.1f}%<br>' +
                      'Total Usuarios: %{customdata[0]}<br>' +
                      'Usuarios Activos: %{customdata[1]}<extra></extra>'
    )
    
    return fig

# FUNCIÓN: Mapa de calor de adopción SAI por País y Área - OPTIMIZADA CON COLORES ROJO-VERDE
def create_adoption_heatmap(filtered_data):
    """
    Crea mapa de calor de % de adopción de SAI por País y Área
    OPTIMIZADO: Colores rojos para valores bajos y verdes para valores altos
    """
    # Calcular adopción por país y área
    adoption_data = []
    
    for country in filtered_data['PAIS'].unique():
        for area in filtered_data['AREA'].unique():
            subset = filtered_data[
                (filtered_data['PAIS'] == country) & 
                (filtered_data['AREA'] == area)
            ]
            
            if len(subset) > 0:
                total_users = subset['NOMBRE'].nunique()
                active_users = subset[subset['usos_ia'] > 0]['NOMBRE'].nunique()
                adoption_rate = (active_users / total_users) * 100 if total_users > 0 else 0
                
                adoption_data.append({
                    'País': country,
                    'Área': area,
                    'Porcentaje_Adopcion': adoption_rate,
                    'Total_Usuarios': total_users,
                    'Usuarios_Activos': active_users
                })
    
    if not adoption_data:
        # Si no hay datos, crear gráfico vacío
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos suficientes para generar el mapa de calor",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title='🔥 Mapa de Calor: % Adopción SAI por País y Área')
        return fig
    
    adoption_df = pd.DataFrame(adoption_data)
    
    # Crear matriz pivot para el heatmap
    heatmap_data = adoption_df.pivot(index='Área', columns='País', values='Porcentaje_Adopcion')
    
    # OPTIMIZACIÓN PRINCIPAL: Cambiar escala de colores a rojo-verde
    # Rojo para valores bajos, verde para valores altos
    fig = px.imshow(
        heatmap_data,
        title='🔥 Mapa de Calor: % Adopción SAI por País y Área',
        color_continuous_scale='RdYlGn',  # CAMBIO: De 'RdYlBu_r' a 'RdYlGn' (rojo-amarillo-verde)
        aspect='auto',
        labels=dict(x="País", y="Área", color="% Adopción")
    )
    
    # Personalizar el heatmap
    fig.update_layout(
        xaxis_title="País",
        yaxis_title="Área",
        coloraxis_colorbar=dict(title="% Adopción SAI")
    )
    
    # Añadir valores de texto en cada celda
    fig.update_traces(
        hovertemplate='<b>País:</b> %{x}<br>' +
                      '<b>Área:</b> %{y}<br>' +
                      '<b>Adopción:</b> %{z:.1f}%<extra></extra>',
        texttemplate="%{z:.1f}%",
        textfont={"size": 10}
    )
    
    return fig

# FUNCIÓN: Gráfico de % Adopción vs Tiempo
def create_adoption_trend(filtered_data, selected_months):
    """
    Crea gráfico de tendencia de % de adopción a lo largo del tiempo
    """
    # Ordenar los meses seleccionados cronológicamente
    selected_months_sorted = sort_months_chronologically(selected_months)
    
    # Calcular % de adopción para cada mes
    adoption_data = []
    
    for month in selected_months_sorted:
        month_data = filtered_data[filtered_data['Mes'] == month]
        total_users = month_data['NOMBRE'].nunique()
        users_with_usage = month_data[month_data['usos_ia'] > 0]['NOMBRE'].nunique()
        
        adoption_percentage = (users_with_usage / total_users) * 100 if total_users > 0 else 0
        
        adoption_data.append({
            'Mes': month,
            'Porcentaje_Adopcion': adoption_percentage,
            'Usuarios_Activos': users_with_usage,
            'Total_Usuarios': total_users
        })
    
    adoption_df = pd.DataFrame(adoption_data)
    
    # Crear gráfico de línea con marcadores
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=adoption_df['Mes'],
        y=adoption_df['Porcentaje_Adopcion'],
        mode='lines+markers',
        name='% Adopción',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8, color='#1f77b4'),
        hovertemplate='<b>%{x}</b><br>' +
                      'Adopción: %{y:.1f}%<br>' +
                      'Usuarios Activos: %{customdata[0]}<br>' +
                      'Total Usuarios: %{customdata[1]}<extra></extra>',
        customdata=adoption_df[['Usuarios_Activos', 'Total_Usuarios']].values
    ))
    
    # Añadir línea de tendencia si hay más de un punto
    if len(adoption_df) > 1:
        x_numeric = list(range(len(adoption_df)))
        y_values = adoption_df['Porcentaje_Adopcion'].values
        z = np.polyfit(x_numeric, y_values, 1)
        p = np.poly1d(z)
        
        fig.add_trace(go.Scatter(
            x=adoption_df['Mes'],
            y=p(x_numeric),
            mode='lines',
            name='Tendencia',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='Tendencia: %{y:.1f}%<extra></extra>'
        ))
    
    fig.update_layout(
        title='📈 Evolución del % de Adopción de SAI por Mes',
        xaxis_title='Mes',
        yaxis_title='Porcentaje de Adopción (%)',
        hovermode='x unified',
        showlegend=True,
        height=400
    )
    
    return fig

# ==========================================
# FUNCIONES PARA RANKINGS OPTIMIZADAS (3 TABLAS)
# ==========================================

def create_top_5_users_by_usage(filtered_data):
    """
    Crea tabla de ranking con los top 5 usuarios por uso total de SAI
    """
    # Calcular uso total por usuario
    user_usage = filtered_data.groupby(['NOMBRE', 'PAIS', 'AREA', 'CARGO']).agg({
        'usos_ia': 'sum'
    }).reset_index()
    
    # Ordenar por uso total de mayor a menor y tomar top 5
    user_usage = user_usage.sort_values('usos_ia', ascending=False).head(5)
    
    # Agregar columna de posición
    user_usage.insert(0, 'Posición', range(1, len(user_usage) + 1))
    
    # Renombrar columnas para mejor presentación
    user_usage = user_usage.rename(columns={
        'NOMBRE': 'Usuario',
        'PAIS': 'País',
        'AREA': 'Área',
        'CARGO': 'Cargo',
        'usos_ia': 'Total Usos SAI'
    })
    
    return user_usage

def create_top_5_countries_by_usage(filtered_data):
    """
    Crea tabla de ranking con los top 5 países por uso total de SAI
    """
    # Calcular uso total por país
    country_usage = filtered_data.groupby('PAIS').agg({
        'usos_ia': 'sum',
        'NOMBRE': 'nunique'
    }).reset_index()
    
    # Ordenar por uso total de mayor a menor y tomar top 5
    country_usage = country_usage.sort_values('usos_ia', ascending=False).head(5)
    
    # Agregar columna de posición
    country_usage.insert(0, 'Posición', range(1, len(country_usage) + 1))
    
    # Renombrar columnas para mejor presentación
    country_usage = country_usage.rename(columns={
        'PAIS': 'País',
        'usos_ia': 'Total Usos SAI',
        'NOMBRE': 'Total Usuarios'
    })
    
    return country_usage

def create_top_5_countries_by_adoption(filtered_data):
    """
    Crea tabla de ranking con los top 5 países por porcentaje de adopción de SAI
    """
    # Calcular adopción por país
    country_adoption = []
    
    for country in filtered_data['PAIS'].unique():
        country_data = filtered_data[filtered_data['PAIS'] == country]
        total_users = country_data['NOMBRE'].nunique()
        active_users = country_data[country_data['usos_ia'] > 0]['NOMBRE'].nunique()
        
        adoption_rate = (active_users / total_users) * 100 if total_users > 0 else 0
        
        country_adoption.append({
            'País': country,
            'Total_Usuarios': total_users,
            'Usuarios_Activos': active_users,
            'Porcentaje_Adopcion': adoption_rate
        })
    
    adoption_df = pd.DataFrame(country_adoption)
    
    # Ordenar por porcentaje de adopción de mayor a menor y tomar top 5
    adoption_df = adoption_df.sort_values('Porcentaje_Adopcion', ascending=False).head(5)
    
    # Agregar columna de posición
    adoption_df.insert(0, 'Posición', range(1, len(adoption_df) + 1))
    
    # Renombrar columnas para mejor presentación
    adoption_df = adoption_df.rename(columns={
        'Total_Usuarios': 'Total Usuarios',
        'Usuarios_Activos': 'Usuarios Activos',
        'Porcentaje_Adopcion': '% Adopción'
    })
    
    # Redondear porcentaje de adopción
    adoption_df['% Adopción'] = adoption_df['% Adopción'].round(1)
    
    return adoption_df

def show_rankings_section(filtered_data):
    """
    Muestra la sección de rankings con 3 tablas: Top 5 Usuarios, Top 5 Países por Uso y Top 5 Países por Adopción
    """
    st.subheader("🏆 Rankings SAI")
    st.markdown("Análisis de los mejores performers durante el período seleccionado.")
    
    # Crear las tres tablas de ranking
    top_5_users = create_top_5_users_by_usage(filtered_data)
    top_5_countries_usage = create_top_5_countries_by_usage(filtered_data)
    top_5_countries_adoption = create_top_5_countries_by_adoption(filtered_data)
    
    # Organizar en 3 columnas para mostrar las tablas lado a lado
    col1, col2, col3 = st.columns(3)
    
    # TABLA 1: Top 5 Usuarios de SAI
    with col1:
        st.markdown("#### 👤 Top 5 Usuarios de SAI")
        if len(top_5_users) > 0:
            st.dataframe(top_5_users, use_container_width=True, hide_index=True)
            
            # Botón de descarga
            csv_users = top_5_users.to_csv(index=False)
            st.download_button(
                label="📥 Descargar",
                data=csv_users,
                file_name=f'top_5_usuarios_sai_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                key="download_top_5_users"
            )
        else:
            st.warning("⚠️ No hay datos suficientes")
    
    # TABLA 2: Top 5 Países por Uso
    with col2:
        st.markdown("#### 🌍 Top 5 Países por Uso")
        if len(top_5_countries_usage) > 0:
            st.dataframe(top_5_countries_usage, use_container_width=True, hide_index=True)
            
            # Botón de descarga
            csv_countries_usage = top_5_countries_usage.to_csv(index=False)
            st.download_button(
                label="📥 Descargar",
                data=csv_countries_usage,
                file_name=f'top_5_paises_uso_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                key="download_top_5_countries_usage"
            )
        else:
            st.warning("⚠️ No hay datos suficientes")
    
    # TABLA 3: Top 5 Países por Adopción
    with col3:
        st.markdown("#### 🎯 Top 5 Países por Adopción")
        if len(top_5_countries_adoption) > 0:
            st.dataframe(top_5_countries_adoption, use_container_width=True, hide_index=True)
            
            # Botón de descarga
            csv_countries_adoption = top_5_countries_adoption.to_csv(index=False)
            st.download_button(
                label="📥 Descargar",
                data=csv_countries_adoption,
                file_name=f'top_5_paises_adopcion_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                key="download_top_5_countries_adoption"
            )
        else:
            st.warning("⚠️ No hay datos suficientes")
    
    # Mostrar insights de los líderes
    st.markdown("---")
    st.markdown("#### 📊 Insights de Liderazgo")
    
    # Crear 3 columnas para los insights
    insight_col1, insight_col2, insight_col3 = st.columns(3)
    
    # Insight del usuario líder
    with insight_col1:
        if len(top_5_users) > 0:
            top_user = top_5_users.iloc[0]
            st.info(f"""
            **🥇 Usuario Líder:**
            
            **{top_user['Usuario']}**
            
            📊 **{top_user['Total Usos SAI']}** usos totales
            
            🌍 **{top_user['País']}** - **{top_user['Área']}**
            """)
        else:
            st.warning("Sin datos de usuarios")
    
    # Insight del país líder por uso
    with insight_col2:
        if len(top_5_countries_usage) > 0:
            top_country_usage = top_5_countries_usage.iloc[0]
            st.success(f"""
            **🥇 País Líder en Uso:**
            
            **{top_country_usage['País']}**
            
            📊 **{top_country_usage['Total Usos SAI']}** usos totales
            
            👥 **{top_country_usage['Total Usuarios']}** usuarios
            """)
        else:
            st.warning("Sin datos de países")
    
    # Insight del país líder por adopción
    with insight_col3:
        if len(top_5_countries_adoption) > 0:
            top_country_adoption = top_5_countries_adoption.iloc[0]
            st.info(f"""
            **🥇 País Líder en Adopción:**
            
            **{top_country_adoption['País']}**
            
            📊 **{top_country_adoption['% Adopción']}%** de adopción
            
            👥 **{top_country_adoption['Usuarios Activos']}**/**{top_country_adoption['Total Usuarios']}** usuarios
            """)
        else:
            st.warning("Sin datos de adopción")

# FUNCIÓN: Mostrar mensaje de advertencia cuando no hay meses seleccionados
def show_no_months_warning():
    """
    Muestra un mensaje de advertencia cuando no hay meses seleccionados
    """
    st.warning("⚠️ **Selecciona al menos un mes para continuar.**")
    st.info("👆 Por favor, selecciona uno o más meses en el filtro de la barra lateral para visualizar los datos.")
    
    st.markdown("""
    <div style="
        padding: 2rem;
        border: 2px dashed #ffa500;
        border-radius: 10px;
        text-align: center;
        background-color: #fff3cd;
        margin: 2rem 0;
    ">
        <h3 style="color: #856404;">📅 Sin meses seleccionados</h3>
        <p style="color: #856404; margin: 0;">
            Para continuar con el análisis, selecciona al menos un mes en los filtros de la barra lateral.
        </p>
    </div>
    """, unsafe_allow_html=True)

# FUNCIÓN: Mostrar mensaje de advertencia cuando no hay filtros seleccionados
def show_no_filters_warning():
    """
    Muestra un mensaje de advertencia cuando no hay países o áreas seleccionados
    """
    st.warning("⚠️ **Selecciona al menos un país y un área para continuar.**")
    st.info("👆 Por favor, selecciona uno o más países y áreas en los filtros de la barra lateral para visualizar los datos.")
    
    st.markdown("""
    <div style="
        padding: 2rem;
        border: 2px dashed #ff6b6b;
        border-radius: 10px;
        text-align: center;
        background-color: #ffe0e0;
        margin: 2rem 0;
    ">
        <h3 style="color: #d63031;">🎯 Sin filtros seleccionados</h3>
        <p style="color: #d63031; margin: 0;">
            Para continuar con el análisis, selecciona al menos un país y un área en los filtros de la barra lateral.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# FUNCIONES OPTIMIZADAS PARA ESTADÍSTICAS DETALLADAS
# ==========================================

def create_detailed_country_statistics(filtered_data):
    """
    Crea estadísticas detalladas por país con todas las métricas solicitadas
    
    Returns:
        pd.DataFrame: DataFrame con estadísticas completas por país
    """
    country_stats = []
    
    for country in filtered_data['PAIS'].unique():
        country_data = filtered_data[filtered_data['PAIS'] == country]
        
        # Métricas básicas
        total_professionals = country_data['NOMBRE'].nunique()
        active_users = country_data[country_data['usos_ia'] > 0]['NOMBRE'].nunique()
        adoption_rate = (active_users / total_professionals) * 100 if total_professionals > 0 else 0
        
        # Métricas de uso
        total_usage = country_data['usos_ia'].sum()
        avg_usage_per_user = total_usage / total_professionals if total_professionals > 0 else 0
        
        # Calcular desviación estándar por usuario
        user_usage_totals = country_data.groupby('NOMBRE')['usos_ia'].sum()
        std_deviation = user_usage_totals.std() if len(user_usage_totals) > 1 else 0
        
        country_stats.append({
            'País': country,
            'Total Profesionales Elegibles': total_professionals,
            'Usuarios Activos': active_users,
            '% de Adopción': round(adoption_rate, 1),
            'Cantidad de Usos': int(total_usage),
            'Uso Promedio por Usuario': round(avg_usage_per_user, 2),
            'Desviación Estándar': round(std_deviation, 2)
        })
    
    # Convertir a DataFrame y ordenar por adopción
    stats_df = pd.DataFrame(country_stats)
    stats_df = stats_df.sort_values('% de Adopción', ascending=False)
    
    return stats_df

def create_detailed_area_statistics(filtered_data):
    """
    Crea estadísticas detalladas por área con todas las métricas solicitadas
    
    Returns:
        pd.DataFrame: DataFrame con estadísticas completas por área
    """
    area_stats = []
    
    for area in filtered_data['AREA'].unique():
        area_data = filtered_data[filtered_data['AREA'] == area]
        
        # Métricas básicas
        total_professionals = area_data['NOMBRE'].nunique()
        active_users = area_data[area_data['usos_ia'] > 0]['NOMBRE'].nunique()
        adoption_rate = (active_users / total_professionals) * 100 if total_professionals > 0 else 0
        
        # Métricas de uso
        total_usage = area_data['usos_ia'].sum()
        avg_usage_per_user = total_usage / total_professionals if total_professionals > 0 else 0
        
        # Calcular desviación estándar por usuario
        user_usage_totals = area_data.groupby('NOMBRE')['usos_ia'].sum()
        std_deviation = user_usage_totals.std() if len(user_usage_totals) > 1 else 0
        
        area_stats.append({
            'Área': area,
            'Total Profesionales Elegibles': total_professionals,
            'Usuarios Activos': active_users,
            '% de Adopción': round(adoption_rate, 1),
            'Cantidad de Usos': int(total_usage),
            'Uso Promedio por Usuario': round(avg_usage_per_user, 2),
            'Desviación Estándar': round(std_deviation, 2)
        })
    
    # Convertir a DataFrame y ordenar por adopción
    stats_df = pd.DataFrame(area_stats)
    stats_df = stats_df.sort_values('% de Adopción', ascending=False)
    
    return stats_df

def show_detailed_statistics_section(filtered_data):
    """
    Muestra la sección de estadísticas detalladas con tablas optimizadas por país y área
    """
    st.subheader("📈 Resumen Estadístico por Dimensiones")
    st.markdown("Análisis estadístico completo con métricas avanzadas de adopción y uso.")
    
    # Crear las estadísticas detalladas
    country_stats = create_detailed_country_statistics(filtered_data)
    area_stats = create_detailed_area_statistics(filtered_data)
    
    # TABLA 1: Estadísticas por País
    st.markdown("#### 🌍 **Estadísticas Detalladas por País**")
    st.markdown("*Análisis completo de adopción y uso de SAI por país con métricas estadísticas avanzadas.*")
    
    if len(country_stats) > 0:
        # Mostrar tabla con formato mejorado
        st.dataframe(
            country_stats, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "País": st.column_config.TextColumn("🌍 País", width="medium"),
                "Total Profesionales Elegibles": st.column_config.NumberColumn("👥 Total Profesionales", format="%d"),
                "Usuarios Activos": st.column_config.NumberColumn("🚀 Usuarios Activos", format="%d"),
                "% de Adopción": st.column_config.NumberColumn("🎯 % Adopción", format="%.1f%%"),
                "Cantidad de Usos": st.column_config.NumberColumn("📊 Total Usos", format="%d"),
                "Uso Promedio por Usuario": st.column_config.NumberColumn("📈 Promedio/Usuario", format="%.2f"),
                "Desviación Estándar": st.column_config.NumberColumn("📉 Desv. Estándar", format="%.2f")
            }
        )
        
        # Botón de descarga para estadísticas por país
        csv_country_stats = country_stats.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Estadísticas por País",
            data=csv_country_stats,
            file_name=f'estadisticas_detalladas_pais_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
            key="download_country_detailed_stats"
        )
        
        # Insights destacados por país
        with st.expander("💡 Insights Destacados - Países"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                top_adoption_country = country_stats.iloc[0]
                st.success(f"""
                **🥇 Mayor Adopción:**
                
                **{top_adoption_country['País']}**
                
                📊 {top_adoption_country['% de Adopción']}% adopción
                
                👥 {top_adoption_country['Usuarios Activos']}/{top_adoption_country['Total Profesionales Elegibles']} usuarios
                """)
            
            with col2:
                top_usage_country = country_stats.loc[country_stats['Cantidad de Usos'].idxmax()]
                st.info(f"""
                **🚀 Mayor Uso Total:**
                
                **{top_usage_country['País']}**
                
                📈 {top_usage_country['Cantidad de Usos']} usos totales
                
                📊 {top_usage_country['Uso Promedio por Usuario']:.1f} promedio/usuario
                """)
            
            with col3:
                most_consistent_country = country_stats.loc[country_stats['Desviación Estándar'].idxmin()]
                st.warning(f"""
                **⚖️ Uso Más Consistente:**
                
                **{most_consistent_country['País']}**
                
                📉 {most_consistent_country['Desviación Estándar']:.2f} desv. estándar
                
                📈 {most_consistent_country['Uso Promedio por Usuario']:.1f} promedio/usuario
                """)
    else:
        st.warning("⚠️ No hay datos suficientes para generar estadísticas por país")
    
    st.markdown("---")
    
    # TABLA 2: Estadísticas por Área
    st.markdown("#### 🏢 **Estadísticas Detalladas por Área**")
    st.markdown("*Análisis completo de adopción y uso de SAI por área funcional con métricas estadísticas avanzadas.*")
    
    if len(area_stats) > 0:
        # Mostrar tabla con formato mejorado
        st.dataframe(
            area_stats, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Área": st.column_config.TextColumn("🏢 Área", width="medium"),
                "Total Profesionales Elegibles": st.column_config.NumberColumn("👥 Total Profesionales", format="%d"),
                "Usuarios Activos": st.column_config.NumberColumn("🚀 Usuarios Activos", format="%d"),
                "% de Adopción": st.column_config.NumberColumn("🎯 % Adopción", format="%.1f%%"),
                "Cantidad de Usos": st.column_config.NumberColumn("📊 Total Usos", format="%d"),
                "Uso Promedio por Usuario": st.column_config.NumberColumn("📈 Promedio/Usuario", format="%.2f"),
                "Desviación Estándar": st.column_config.NumberColumn("📉 Desv. Estándar", format="%.2f")
            }
        )
        
        # Botón de descarga para estadísticas por área
        csv_area_stats = area_stats.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Estadísticas por Área",
            data=csv_area_stats,
            file_name=f'estadisticas_detalladas_area_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
            key="download_area_detailed_stats"
        )
        
        # Insights destacados por área
        with st.expander("💡 Insights Destacados - Áreas"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                top_adoption_area = area_stats.iloc[0]
                st.success(f"""
                **🥇 Mayor Adopción:**
                
                **{top_adoption_area['Área']}**
                
                📊 {top_adoption_area['% de Adopción']}% adopción
                
                👥 {top_adoption_area['Usuarios Activos']}/{top_adoption_area['Total Profesionales Elegibles']} usuarios
                """)
            
            with col2:
                top_usage_area = area_stats.loc[area_stats['Cantidad de Usos'].idxmax()]
                st.info(f"""
                **🚀 Mayor Uso Total:**
                
                **{top_usage_area['Área']}**
                
                📈 {top_usage_area['Cantidad de Usos']} usos totales
                
                📊 {top_usage_area['Uso Promedio por Usuario']:.1f} promedio/usuario
                """)
            
            with col3:
                most_consistent_area = area_stats.loc[area_stats['Desviación Estándar'].idxmin()]
                st.warning(f"""
                **⚖️ Uso Más Consistente:**
                
                **{most_consistent_area['Área']}**
                
                📉 {most_consistent_area['Desviación Estándar']:.2f} desv. estándar
                
                📈 {most_consistent_area['Uso Promedio por Usuario']:.1f} promedio/usuario
                """)
    else:
        st.warning("⚠️ No hay datos suficientes para generar estadísticas por área")
    
    # Resumen comparativo
    st.markdown("---")
    st.markdown("#### 📊 **Resumen Comparativo General**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if len(country_stats) > 0:
            st.metric(
                "🌍 Países Analizados", 
                len(country_stats),
                help="Número total de países incluidos en el análisis"
            )
            st.metric(
                "📈 Adopción Promedio (Países)", 
                f"{country_stats['% de Adopción'].mean():.1f}%",
                help="Porcentaje promedio de adopción entre todos los países"
            )
    
    with col2:
        if len(area_stats) > 0:
            st.metric(
                "🏢 Áreas Analizadas", 
                len(area_stats),
                help="Número total de áreas funcionales incluidas en el análisis"
            )
            st.metric(
                "📈 Adopción Promedio (Áreas)", 
                f"{area_stats['% de Adopción'].mean():.1f}%",
                help="Porcentaje promedio de adopción entre todas las áreas"
            )

# ==========================================
# FUNCIONES PARA LAS NUEVAS PESTAÑAS
# ==========================================

def show_dashboard_tab(filtered_data, selected_months, selected_countries, selected_areas, chart_conditions):
    """
    Muestra el contenido de la pestaña Dashboard
    """
    # SECCIÓN: Métricas principales
    st.header("📊 Métricas Principales")
    create_metrics(None, filtered_data, selected_months)
    st.markdown("---")

    # SECCIÓN: Análisis de Adopción SAI
    st.header("🎯 Análisis de Adopción SAI")
    
    # Gráfico 1: Evolución de Adopción
    st.subheader("📈 Evolución del % de Adopción por Mes")
    if chart_conditions['show_adoption_trend']:
        description = generate_chart_description('trend', selected_months, selected_countries, selected_areas)
        st.markdown(f"*{description}*")
        
        fig_adoption_trend = create_adoption_trend(filtered_data, selected_months)
        st.plotly_chart(fig_adoption_trend, use_container_width=True)
    else:
        show_chart_requirement_message("adoption_trend", "multiple_months")
    st.markdown("---")
    
    # Gráfico 2: Adopción por País
    st.subheader("🌎 % Adopción SAI por País")
    if chart_conditions['show_adoption_by_country']:
        description = generate_chart_description('country', selected_months, selected_countries, selected_areas)
        st.markdown(f"*{description}*")
        
        fig_adoption_country = create_adoption_by_country(filtered_data)
        st.plotly_chart(fig_adoption_country, use_container_width=True)
    else:
        show_chart_requirement_message("adoption_by_country", "multiple_countries")
    st.markdown("---")
    
    # Gráfico 3: Mapa de Calor
    st.subheader("🔥 Mapa de Calor: % Adopción SAI por País y Área")
    if chart_conditions['show_adoption_heatmap']:
        description = generate_chart_description('heatmap', selected_months, selected_countries, selected_areas)
        st.markdown(f"*{description}*")
        
        fig_adoption_heatmap = create_adoption_heatmap(filtered_data)
        st.plotly_chart(fig_adoption_heatmap, use_container_width=True)
    else:
        show_chart_requirement_message("adoption_heatmap", "multiple_dimensions")

    # SECCIÓN: Análisis Detallado Adicional
    st.markdown("---")
    st.header("📋 Análisis Detallado Adicional")

    # Sub-pestañas dentro del dashboard
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "🏆 Rankings",
        "📄 Datos Filtrados", 
        "📈 Resumen Estadístico"
    ])

    with sub_tab1:
        show_rankings_section(filtered_data)

    with sub_tab2:
        st.subheader("📄 Datos Filtrados Completos")
        st.dataframe(filtered_data, use_container_width=True)

        # Botón de descarga
        csv = filtered_data.to_csv(index=False)
        st.download_button(
            label="📥 Descargar datos filtrados completos",
            data=csv,
            file_name='datos_filtrados_adopcion_completos.csv',
            mime='text/csv'
        )

    with sub_tab3:
        show_detailed_statistics_section(filtered_data)

def show_executive_summary_tab(filtered_data, selected_months, selected_countries, selected_areas, filter_type):
    """
    Muestra el contenido de la pestaña Resumen Ejecutivo usando IA
    """
    st.header("🤖 Resumen Ejecutivo con IA")
    st.markdown("Genera un resumen ejecutivo inteligente de todos los datos visibles usando inteligencia artificial.")
    
    # OPTIMIZACIÓN PRINCIPAL: Usar session_state para mantener la API Key
    if 'executive_api_key' not in st.session_state:
        st.session_state.executive_api_key = ""
    
    # Configuración de API Key
    col1, col2 = st.columns([2, 1])
    
    with col1:
        api_key = st.text_input(
            "🔑 API Key",
            type="password",
            placeholder="Ingresa tu API Key para el servicio de LLM",
            help="Clave de API necesaria para acceder al servicio de generación de resúmenes",
            value=st.session_state.executive_api_key,
            key="executive_api_key_input"
        )
        # Actualizar session_state cuando cambie el input
        st.session_state.executive_api_key = api_key
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Espaciado
        generate_summary = st.button(
            "🚀 Generar Resumen Ejecutivo",
            type="primary",
            disabled=not api_key,
            help="Genera un resumen ejecutivo inteligente de todos los datos visibles"
        )
    
    # Mostrar información sobre qué datos se incluirán
    with st.expander("ℹ️ ¿Qué información se incluye en el resumen ejecutivo?"):
        st.markdown("""
        El resumen ejecutivo incluirá toda la información visible basada en los filtros seleccionados:
        
        **📊 Métricas Principales:**
        - Total de profesionales elegibles
        - Usuarios activos e inactivos
        - Porcentajes de adopción (acumulado y promedio)
        
        **📈 Análisis Detallado:**
        - Adopción por mes y país
        - Estadísticas descriptivas
        - Tendencias y patrones identificados
        
        **🎯 Filtros Aplicados:**
        - Período temporal seleccionado
        - Países y áreas incluidos
        """)
    
    # Generar resumen si se presiona el botón
    if generate_summary:
        if not api_key:
            st.error("⚠️ Por favor, ingresa tu API Key para continuar.")
            return
        
        # Mostrar indicador de carga
        with st.spinner("🤖 Generando resumen ejecutivo... Esto puede tomar unos momentos."):
            # Generar texto con toda la información
            summary_input_text = generate_summary_text(
                filtered_data, 
                selected_months, 
                selected_countries, 
                selected_areas, 
                filter_type
            )
            
            # Llamar al LLM
            llm_response = generate_llm_summary(summary_input_text, api_key)
        
        # Mostrar resultado
        st.subheader("📋 Resumen Ejecutivo Generado")
        
        # Verificar si hubo error
        if llm_response.startswith("Error"):
            st.error(f"❌ {llm_response}")
            st.info("💡 Verifica que tu API Key sea correcta y que tengas conexión a internet.")
        else:
            # Mostrar resumen exitoso
            st.success("✅ Resumen ejecutivo generado exitosamente")
            
            # Mostrar el resumen en un contenedor estilizado
            st.markdown("""
            <div style="
                background-color: #f8f9fa;
                border-left: 4px solid #007bff;
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
            ">
            """, unsafe_allow_html=True)
            
            st.markdown(llm_response)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Botón para descargar el resumen
            st.download_button(
                label="📥 Descargar Resumen Ejecutivo",
                data=llm_response,
                file_name=f"resumen_ejecutivo_sai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                help="Descarga el resumen ejecutivo generado como archivo de texto"
            )
        
        # Mostrar datos de entrada (opcional, en expander)
        with st.expander("🔍 Ver datos de entrada enviados al LLM"):
            st.text_area(
                "Información enviada al LLM:",
                value=summary_input_text,
                height=300,
                disabled=True
            )

def show_insights_tab(filtered_data, selected_months, selected_countries, selected_areas, filter_type):
    """
    PESTAÑA OPTIMIZADA: Insights Dashboard con IA - Responde preguntas específicas del usuario
    """
    st.header("💡 Insights Dashboard con IA")
    st.markdown("Haz preguntas específicas sobre los datos del dashboard y obtén respuestas inteligentes usando IA.")
    
    # OPTIMIZACIÓN PRINCIPAL: Usar session_state para mantener la API Key y pregunta
    if 'insights_api_key' not in st.session_state:
        st.session_state.insights_api_key = ""
    if 'insights_pregunta' not in st.session_state:
        st.session_state.insights_pregunta = ""
    
    # Configuración de API Key y pregunta del usuario
    col1, col2 = st.columns([2, 1])
    
    with col1:
        api_key = st.text_input(
            "🔑 API Key",
            type="password",
            placeholder="Ingresa tu API Key para el servicio de LLM",
            help="Clave de API necesaria para acceder al servicio de generación de insights",
            value=st.session_state.insights_api_key,
            key="insights_api_key_input"
        )
        # Actualizar session_state cuando cambie el input
        st.session_state.insights_api_key = api_key
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Espaciado
        generate_insights = st.button(
            "🚀 Obtener Respuesta",
            type="primary",
            disabled=not api_key,
            help="Genera respuesta inteligente a tu pregunta específica"
        )
    
    # Campo de pregunta del usuario con ejemplos en placeholder
    pregunta = st.text_area(
        "❓ **Escribe tu pregunta sobre los datos:**",
        placeholder="¿Cuánto creció la adopción SAI en Colombia los últimos meses?",
        height=100,
        help="Escribe cualquier pregunta específica sobre los datos del dashboard",
        value=st.session_state.insights_pregunta,
        key="insights_pregunta_input"
    )
    # Actualizar session_state cuando cambie el input
    st.session_state.insights_pregunta = pregunta
    
    # Mostrar ejemplos de preguntas sugeridas
    with st.expander("💡 Ejemplos de preguntas que puedes hacer"):
        st.markdown("""
        **📈 Preguntas sobre Tendencias:**
        - ¿Cuánto creció la adopción SAI en Colombia los últimos meses?
        - ¿Cuál es la tendencia de adopción en el período seleccionado?
        - ¿Qué meses tuvieron mejor performance?
        
        **🌍 Preguntas sobre Países:**
        - ¿Qué país tiene mejor performance en adopción?
        - ¿Cuáles son las diferencias entre países?
        - ¿Qué países necesitan más apoyo?
        
        **🏢 Preguntas sobre Áreas:**
        - ¿Cuáles son las tendencias por área funcional?
        - ¿Qué área tiene mayor potencial de crecimiento?
        - ¿Cómo se comparan las diferentes áreas?
        
        **🔍 Preguntas Analíticas:**
        - ¿Qué factores influyen en la adopción de SAI?
        - ¿Cuáles son los principales insights de los datos?
        - ¿Qué recomendaciones darías para mejorar la adopción?
        """)
    
    # Generar respuesta si se presiona el botón
    if generate_insights:
        if not api_key:
            st.error("⚠️ Por favor, ingresa tu API Key para continuar.")
            return
        
        if not pregunta.strip():
            st.error("⚠️ Por favor, escribe una pregunta para obtener una respuesta.")
            return
        
        # Mostrar indicador de carga
        with st.spinner("💡 Analizando datos y generando respuesta... Esto puede tomar unos momentos."):
            # Generar texto con toda la información (variable 'data')
            data = generate_summary_text(
                filtered_data, 
                selected_months, 
                selected_countries, 
                selected_areas, 
                filter_type
            )
            
            # Llamar al LLM con la pregunta específica
            llm_response = generate_llm_question_response(data, pregunta, api_key)
        
        # Mostrar resultado
        st.subheader("💡 Respuesta Generada")
        
        # Mostrar la pregunta del usuario
        st.markdown(f"**❓ Tu pregunta:** *{pregunta}*")
        st.markdown("---")
        
        # Verificar si hubo error
        if llm_response.startswith("Error"):
            st.error(f"❌ {llm_response}")
            st.info("💡 Verifica que tu API Key sea correcta y que tengas conexión a internet.")
        else:
            # Mostrar respuesta exitosa
            st.success("✅ Respuesta generada exitosamente")
            
            # Mostrar la respuesta en un contenedor estilizado
            st.markdown("""
            <div style="
                background-color: #f0f8ff;
                border-left: 4px solid #4CAF50;
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
            ">
            """, unsafe_allow_html=True)
            
            st.markdown(llm_response)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Botón para descargar la respuesta
            download_content = f"PREGUNTA:\n{pregunta}\n\n" + "="*50 + f"\n\nRESPUESTA:\n{llm_response}"
            st.download_button(
                label="📥 Descargar Pregunta y Respuesta",
                data=download_content,
                file_name=f"pregunta_respuesta_sai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                help="Descarga la pregunta y respuesta generada como archivo de texto"
            )
        
        # Mostrar datos de entrada (opcional, en expander)
        with st.expander("🔍 Ver datos enviados al LLM"):
            st.text_area(
                "Datos enviados al LLM (variable 'data'):",
                value=data,
                height=200,
                disabled=True,
                key="insights_data_text"
            )
            
            st.text_input(
                "Pregunta enviada al LLM (variable 'pregunta'):",
                value=pregunta,
                disabled=True,
                key="insights_pregunta_text"
            )

# ==========================================
# FUNCIÓN PRINCIPAL OPTIMIZADA CON 3 PESTAÑAS
# ==========================================

def main():
    # Título principal
    st.title("🤖 Dashboard de Análisis de Adopción SAI - Áreas internas")
    st.markdown("---")

    # PROCESAMIENTO AUTOMÁTICO DE ARCHIVOS
    with st.spinner("🔄 Procesando archivos automáticamente..."):
        df_original, df_melted, month_columns_sorted = process_input_files()

    if df_melted is not None:
        
        # Información compacta de los datos
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Registros Totales", len(df_melted))
        with col2:
            st.metric("👥 Usuarios Únicos", df_melted['NOMBRE'].nunique())
        with col3:
            st.metric("📅 Meses Disponibles", len(month_columns_sorted))
        
        st.markdown("---")
        
        # FILTROS EN SIDEBAR
        st.sidebar.header("🔍 Filtros de Análisis")

        # Filtros temporales dinámicos
        selected_months, filter_type = create_dynamic_filters(month_columns_sorted)

        # Separador visual
        st.sidebar.markdown("---")

        # Filtros múltiples
        selected_countries, selected_areas = create_multiple_filters(df_melted)

        # VALIDACIONES
        if not selected_months:
            show_no_months_warning()
            return

        if not selected_countries or not selected_areas:
            show_no_filters_warning()
            return

        # Validar condiciones para mostrar gráficos
        chart_conditions = validate_chart_conditions(selected_months, selected_countries, selected_areas)

        # Aplicar filtros
        filtered_data = df_melted.copy()
        filtered_data = filtered_data[filtered_data['PAIS'].isin(selected_countries)]
        filtered_data = filtered_data[filtered_data['AREA'].isin(selected_areas)]
        filtered_data = filtered_data[filtered_data['Mes'].isin(selected_months)]

        # Mostrar información del filtro aplicado
        st.info(f"📊 **Filtro temporal:** {filter_type} | **Meses:** {len(selected_months)} | **Países:** {len(selected_countries)} | **Áreas:** {len(selected_areas)}")

        # ==========================================
        # PESTAÑAS PRINCIPALES - OPTIMIZACIÓN PRINCIPAL
        # ==========================================
        
        tab1, tab2, tab3 = st.tabs([
            "📊 Dashboard",
            "📋 Resumen Ejecutivo IA", 
            "💡 Insights Dashboard IA"
        ])

        # PESTAÑA 1: Dashboard completo
        with tab1:
            show_dashboard_tab(filtered_data, selected_months, selected_countries, selected_areas, chart_conditions)

        # PESTAÑA 2: Resumen Ejecutivo con IA
        with tab2:
            show_executive_summary_tab(filtered_data, selected_months, selected_countries, selected_areas, filter_type)

        # PESTAÑA 3: Insights Dashboard con IA - OPTIMIZADA
        with tab3:
            show_insights_tab(filtered_data, selected_months, selected_countries, selected_areas, filter_type)

    else:
        # Error al procesar archivos
        st.error("❌ **Error al procesar los archivos automáticamente**")
        st.info("🔍 **Verifica que:**")
        st.markdown("""
        - Existan los archivos **areas_personas.xlsx** y **uso_por_mes.xlsx** en el directorio actual
        - El archivo **areas_personas.xlsx** tenga las columnas: NOMBRE, PAIS, CARGO, AREA
        - El archivo **uso_por_mes.xlsx** tenga la columna NOMBRE y columnas de meses
        - Los nombres de usuarios coincidan entre ambos archivos
        - Tengas permisos de lectura sobre los archivos
        """)
        
        # Mostrar directorio actual para referencia
        st.code(f"📂 Directorio actual: {os.getcwd()}")

if __name__ == "__main__":
    main()
