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

# NUEVA FUNCIÓN: Llamada al LLM para generar resumen
def generate_llm_summary(data_text, api_key):
    """
    Genera un resumen usando el LLM a través de la API proporcionada
    
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

# NUEVA FUNCIÓN: Generar texto plano con toda la información visible
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

# NUEVA FUNCIÓN: Mostrar sección de resumen con LLM
def show_llm_summary_section(filtered_data, selected_months, selected_countries, selected_areas, filter_type):
    """
    Muestra la sección de resumen con LLM incluyendo configuración de API y botón de generación
    """
    st.header("🤖 Resumen Inteligente con IA")
    st.markdown("Genera un resumen ejecutivo inteligente de todos los datos visibles usando inteligencia artificial.")
    
    # Configuración de API Key
    col1, col2 = st.columns([2, 1])
    
    with col1:
        api_key = st.text_input(
            "🔑 API Key",
            type="password",
            placeholder="Ingresa tu API Key para el servicio de LLM",
            help="Clave de API necesaria para acceder al servicio de generación de resúmenes"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Espaciado
        generate_summary = st.button(
            "🚀 Generar Resumen",
            type="primary",
            disabled=not api_key,
            help="Genera un resumen inteligente de todos los datos visibles"
        )
    
    # Mostrar información sobre qué datos se incluirán
    with st.expander("ℹ️ ¿Qué información se incluye en el resumen?"):
        st.markdown("""
        El resumen incluirá toda la información visible basada en los filtros seleccionados:
        
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
        - Países incluidos
        """)
    
    # Generar resumen si se presiona el botón
    if generate_summary:
        if not api_key:
            st.error("⚠️ Por favor, ingresa tu API Key para continuar.")
            return
        
        # Mostrar indicador de carga
        with st.spinner("🤖 Generando resumen inteligente... Esto puede tomar unos momentos."):
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
            st.success("✅ Resumen generado exitosamente")
            
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
                label="📥 Descargar Resumen",
                data=llm_response,
                file_name=f"resumen_sai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                help="Descarga el resumen generado como archivo de texto"
            )
        
        # Mostrar datos de entrada (opcional, en expander)
        with st.expander("🔍 Ver datos de entrada enviados al LLM"):
            st.text_area(
                "Información enviada al LLM:",
                value=summary_input_text,
                height=300,
                disabled=True
            )

# NUEVA FUNCIÓN: Validar condiciones para mostrar gráficos
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

# NUEVA FUNCIÓN: Mostrar mensaje informativo cuando no se cumplen condiciones
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

# FUNCIÓN OPTIMIZADA: Formatear listas para mostrar en descripciones - MODIFICADA PARA MOSTRAR TODOS LOS ELEMENTOS
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

# FUNCIÓN OPTIMIZADA: Formatear período temporal para descripciones
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

# FUNCIÓN COMPLETAMENTE OPTIMIZADA: Generar descripción dinámica para gráficos - MODIFICADA PARA MOSTRAR TODOS LOS ELEMENTOS
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

# FUNCIÓN OPTIMIZADA: Filtrar meses por período (EXCLUYE MES ACTUAL)
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

# NUEVA FUNCIÓN: Crear filtros dinámicos según la selección del usuario
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

# NUEVA FUNCIÓN: Crear filtros múltiples con checkboxes (MODIFICADA - SIN FILTRO DE CARGO)
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

# FUNCIÓN MODIFICADA: Cargar y procesar datos automáticamente
@st.cache_data
def load_data():
    """
    Carga y procesa automáticamente el archivo Excel 'resultado_mes.xlsx' desde el directorio actual
    """
    try:
        # Construir la ruta del archivo en el directorio actual
        file_path = os.path.join(os.getcwd(), "resultado_mes.xlsx")
        
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            st.error(f"❌ No se encontró el archivo 'resultado_mes.xlsx' en el directorio: {os.getcwd()}")
            return None, None, None
        
        # Cargar el archivo Excel
        df = pd.read_excel(file_path)

        # Limpiar valores nulos en las columnas básicas
        df['NOMBRE'] = df['NOMBRE'].fillna('Sin Nombre')
        df['PAIS'] = df['PAIS'].fillna('Sin País')
        df['CARGO'] = df['CARGO'].fillna('Sin Cargo')
        df['AREA'] = df['AREA'].fillna('Sin Área')

        # MODIFICADO: Filtrar para excluir área de "Operaciones"
        df = df[df['AREA'].str.lower() != 'operaciones']

        # Identificar columnas de meses (asumiendo que son las últimas columnas)
        basic_columns = ['NOMBRE', 'PAIS', 'CARGO', 'AREA']
        month_columns = [col for col in df.columns if col not in basic_columns]
        
        # Ordenar meses cronológicamente
        month_columns_sorted = sort_months_chronologically(month_columns)

        # Convertir datos a formato long para mejor análisis
        df_melted = pd.melt(
            df,
            id_vars=basic_columns,
            value_vars=month_columns,
            var_name='Mes',
            value_name='usos_ia'
        )

        # Limpiar datos nulos
        df_melted['usos_ia'] = pd.to_numeric(df_melted['usos_ia'], errors='coerce').fillna(0)

        return df, df_melted, month_columns_sorted
        
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo 'resultado_mes.xlsx': {str(e)}")
        return None, None, None

# FUNCIÓN OPTIMIZADA: Crear métricas principales en 2 filas con métricas de adopción
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

# FUNCIÓN MODIFICADA: Gráfico de adopción SAI vs País con ejes fijos de 0 a 100%
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

# FUNCIÓN MODIFICADA: Mapa de calor de adopción SAI por País y Área - OPTIMIZADA CON COLORES ROJO-VERDE
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

# FUNCIÓN OPTIMIZADA: Gráfico de % Adopción vs Tiempo
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

# FUNCIÓN OPTIMIZADA: Mostrar mensaje de advertencia cuando no hay meses seleccionados
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

# NUEVA FUNCIÓN: Mostrar mensaje de advertencia cuando no hay filtros seleccionados
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

# FUNCIÓN PRINCIPAL MODIFICADA: Aplicación principal con carga automática
def main():
    # Título principal
    st.title("🤖 Dashboard de Análisis de Adopción SAI - Áreas internas")
    st.markdown("---")

    # CAMBIO PRINCIPAL: Cargar datos automáticamente
    st.sidebar.header("📁 Estado del Archivo")
    
    # Mostrar información del archivo que se está cargando
    st.sidebar.info("📄 **Archivo:** resultado_mes.xlsx\n\n📂 **Ubicación:** Directorio actual")
    
    # Cargar datos automáticamente
    with st.spinner("🔄 Cargando archivo resultado_mes.xlsx..."):
        df_original, df_melted, month_columns_sorted = load_data()

    if df_melted is not None:
        # Mostrar confirmación de carga exitosa
        st.sidebar.success("✅ Archivo cargado exitosamente")
        st.sidebar.write(f"📊 **Registros:** {len(df_melted)}")
        st.sidebar.write(f"👥 **Usuarios únicos:** {df_melted['NOMBRE'].nunique()}")
        st.sidebar.write(f"📅 **Meses disponibles:** {len(month_columns_sorted)}")
        
        # Filtros en sidebar
        st.sidebar.header("🔍 Filtros")

        # FILTROS DINÁMICOS OPTIMIZADOS: Crear filtros temporales dinámicos
        selected_months, filter_type = create_dynamic_filters(month_columns_sorted)

        # Separador visual
        st.sidebar.markdown("---")

        # FILTROS MÚLTIPLES MODIFICADOS: Sin filtro de cargo
        selected_countries, selected_areas = create_multiple_filters(df_melted)

        # VALIDACIÓN PRINCIPAL: Verificar si hay meses seleccionados
        if not selected_months:
            show_no_months_warning()
            return

        # NUEVA VALIDACIÓN: Verificar si hay países y áreas seleccionados
        if not selected_countries or not selected_areas:
            show_no_filters_warning()
            return

        # NUEVA FUNCIONALIDAD: Validar condiciones para mostrar gráficos
        chart_conditions = validate_chart_conditions(selected_months, selected_countries, selected_areas)

        # Aplicar filtros
        filtered_data = df_melted.copy()

        # Filtrar por países seleccionados
        filtered_data = filtered_data[filtered_data['PAIS'].isin(selected_countries)]

        # Filtrar por áreas seleccionadas
        filtered_data = filtered_data[filtered_data['AREA'].isin(selected_areas)]

        # Filtrar por meses seleccionados
        filtered_data = filtered_data[filtered_data['Mes'].isin(selected_months)]

        # Mostrar información del filtro aplicado (SIN CARGO)
        st.info(f"📊 **Filtro temporal:** {filter_type} | **Meses:** {len(selected_months)} | **Países:** {len(selected_countries)} | **Áreas:** {len(selected_areas)}")

        # SECCIÓN OPTIMIZADA: Mostrar métricas principales en 2 filas (ACTUALIZADA)
        st.header("📊 Métricas Principales")
        create_metrics(df_melted, filtered_data, selected_months)
        st.markdown("---")

        # ==========================================
        # SECCIÓN: RESUMEN INTELIGENTE CON LLM (SIN CARGO)
        # ==========================================
        show_llm_summary_section(filtered_data, selected_months, selected_countries, selected_areas, filter_type)
        st.markdown("---")

        # ==========================================
        # SECCIÓN PRINCIPAL: ANÁLISIS DE ADOPCIÓN SAI CON DESCRIPCIONES DINÁMICAS OPTIMIZADAS
        # ==========================================
        st.header("🎯 Análisis de Adopción SAI")
        
        # Gráfico 1: Evolución de Adopción (VALIDACIÓN: solo si hay más de 1 mes)
        st.subheader("📈 Evolución del % de Adopción por Mes")
        if chart_conditions['show_adoption_trend']:
            # DESCRIPCIÓN COMPLETAMENTE OPTIMIZADA CON FILTROS DINÁMICOS
            description = generate_chart_description('trend', selected_months, selected_countries, selected_areas)
            st.markdown(f"*{description}*")
            
            fig_adoption_trend = create_adoption_trend(filtered_data, selected_months)
            st.plotly_chart(fig_adoption_trend, use_container_width=True)
        else:
            show_chart_requirement_message("adoption_trend", "multiple_months")
        st.markdown("---")
        
        # Gráfico 2: Adopción por País (VALIDACIÓN: solo si hay más de 1 país)
        st.subheader("🌎 % Adopción SAI por País")
        if chart_conditions['show_adoption_by_country']:
            # DESCRIPCIÓN COMPLETAMENTE OPTIMIZADA CON FILTROS DINÁMICOS
            description = generate_chart_description('country', selected_months, selected_countries, selected_areas)
            st.markdown(f"*{description}*")
            
            fig_adoption_country = create_adoption_by_country(filtered_data)
            st.plotly_chart(fig_adoption_country, use_container_width=True)
        else:
            show_chart_requirement_message("adoption_by_country", "multiple_countries")
        st.markdown("---")
        
        # Gráfico 3: Mapa de Calor de Adopción por País y Área (VALIDACIÓN: solo si hay más de 1 país y área)
        st.subheader("🔥 Mapa de Calor: % Adopción SAI por País y Área")
        if chart_conditions['show_adoption_heatmap']:
            # DESCRIPCIÓN COMPLETAMENTE OPTIMIZADA CON FILTROS DINÁMICOS
            description = generate_chart_description('heatmap', selected_months, selected_countries, selected_areas)
            st.markdown(f"*{description}*")
            
            fig_adoption_heatmap = create_adoption_heatmap(filtered_data)
            st.plotly_chart(fig_adoption_heatmap, use_container_width=True)
        else:
            show_chart_requirement_message("adoption_heatmap", "multiple_dimensions")

        # ==========================================
        # SECCIÓN FINAL: ANÁLISIS DETALLADO ADICIONAL (OPTIMIZADA)
        # ==========================================
        st.markdown("---")
        st.header("📋 Análisis Detallado Adicional")

        # PESTAÑAS OPTIMIZADAS: Rankings en primera posición
        tab1, tab2, tab3 = st.tabs([
            "🏆 Rankings",  # PRIMERA PESTAÑA
            "📄 Datos Filtrados", 
            "📈 Resumen Estadístico"  # PESTAÑA OPTIMIZADA
        ])

        # PRIMERA PESTAÑA: Rankings (OPTIMIZADA - 3 TABLAS)
        with tab1:
            show_rankings_section(filtered_data)

        with tab2:
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

        # TERCERA PESTAÑA: Resumen Estadístico COMPLETAMENTE OPTIMIZADO
        with tab3:
            show_detailed_statistics_section(filtered_data)

    else:
        # MENSAJE MODIFICADO: Error al cargar archivo automático
        st.error("❌ **Error al cargar el archivo automáticamente**")
        st.info("🔍 **Verifica que:**")
        st.markdown("""
        - El archivo `resultado_mes.xlsx` existe en el mismo directorio que este script
        - El archivo tiene el formato correcto con las columnas: NOMBRE, PAIS, CARGO, AREA y meses
        - Tienes permisos de lectura sobre el archivo
        """)
        
        # Mostrar directorio actual para referencia
        st.code(f"📂 Directorio actual: {os.getcwd()}")

if __name__ == "__main__":
    main()
