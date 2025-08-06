#ADOPCION
pip install -r requirements.txt
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
def generate_summary_text(filtered_data, selected_months, selected_countries, selected_areas, selected_cargo, filter_type):
    """
    Genera un texto plano con toda la información visible basada en los filtros seleccionados
    
    Args:
        filtered_data: DataFrame con datos filtrados
        selected_months: Lista de meses seleccionados
        selected_countries: Lista de países seleccionados
        selected_areas: Lista de áreas seleccionadas
        selected_cargo: Cargo seleccionado
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
    summary_text += f"- Áreas seleccionadas ({len(selected_areas)}): {', '.join(selected_areas)}\n"
    summary_text += f"- Cargo seleccionado: {selected_cargo}\n\n"
    
    # Métricas principales
    summary_text += "MÉTRICAS PRINCIPALES:\n"
    
    # Total Profesionales Elegibles
    total_eligible_professionals = filtered_data['NOMBRE'].nunique()
    summary_text += f"- Total Profesionales Elegibles: {total_eligible_professionals}\n"
    
    # Total de Usuarios Activos
    active_users = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
    summary_text += f"- Total Usuarios Activos: {active_users}\n"
    
    # Total de usos de IA
    total_usage = int(filtered_data['usos_ia'].sum())
    summary_text += f"- Usos Totales IA: {total_usage:,}\n"
    
    # Promedio mensual
    avg_usage = filtered_data['usos_ia'].mean()
    summary_text += f"- Promedio Mensual: {avg_usage:.1f}\n"
    
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
        'NOMBRE': 'nunique',
        'usos_ia': 'sum'
    }).reset_index()
    
    for _, row in country_data.iterrows():
        country = row['PAIS']
        users = row['NOMBRE']
        usage = row['usos_ia']
        
        # Calcular adopción por país
        country_filtered = filtered_data[filtered_data['PAIS'] == country]
        active_users_country = country_filtered[country_filtered['usos_ia'] > 0]['NOMBRE'].nunique()
        adoption_rate = (active_users_country / users) * 100 if users > 0 else 0
        
        summary_text += f"- {country}: {users} usuarios, {int(usage)} usos totales, {adoption_rate:.1f}% adopción\n"
    
    summary_text += "\n"
    
    # Análisis por área
    summary_text += "ANÁLISIS POR ÁREA:\n"
    area_data = filtered_data.groupby('AREA').agg({
        'NOMBRE': 'nunique',
        'usos_ia': 'sum'
    }).reset_index()
    
    for _, row in area_data.iterrows():
        area = row['AREA']
        users = row['NOMBRE']
        usage = row['usos_ia']
        
        # Calcular adopción por área
        area_filtered = filtered_data[filtered_data['AREA'] == area]
        active_users_area = area_filtered[area_filtered['usos_ia'] > 0]['NOMBRE'].nunique()
        adoption_rate = (active_users_area / users) * 100 if users > 0 else 0
        
        summary_text += f"- {area}: {users} usuarios, {int(usage)} usos totales, {adoption_rate:.1f}% adopción\n"
    
    summary_text += "\n"
    
    # Análisis por cargo
    summary_text += "ANÁLISIS POR CARGO:\n"
    cargo_data = filtered_data.groupby('CARGO').agg({
        'NOMBRE': 'nunique',
        'usos_ia': 'sum'
    }).reset_index()
    
    for _, row in cargo_data.iterrows():
        cargo = row['CARGO']
        users = row['NOMBRE']
        usage = row['usos_ia']
        
        # Calcular adopción por cargo
        cargo_filtered = filtered_data[filtered_data['CARGO'] == cargo]
        active_users_cargo = cargo_filtered[cargo_filtered['usos_ia'] > 0]['NOMBRE'].nunique()
        adoption_rate = (active_users_cargo / users) * 100 if users > 0 else 0
        
        summary_text += f"- {cargo}: {users} usuarios, {int(usage)} usos totales, {adoption_rate:.1f}% adopción\n"
    
    summary_text += "\n"
    
    # Top 10 usuarios
    summary_text += "TOP 10 USUARIOS POR USO DE IA:\n"
    top_users = filtered_data.groupby(['NOMBRE', 'PAIS', 'CARGO', 'AREA'])['usos_ia'].sum().reset_index()
    top_users = top_users.sort_values('usos_ia', ascending=False).head(10)
    
    for i, (_, row) in enumerate(top_users.iterrows(), 1):
        summary_text += f"{i}. {row['NOMBRE']} ({row['PAIS']}, {row['CARGO']}, {row['AREA']}): {int(row['usos_ia'])} usos\n"
    
    summary_text += "\n"
    
    # Estadísticas adicionales
    summary_text += "ESTADÍSTICAS ADICIONALES:\n"
    summary_text += f"- Total de registros analizados: {len(filtered_data)}\n"
    summary_text += f"- Usuarios únicos: {filtered_data['NOMBRE'].nunique()}\n"
    summary_text += f"- Países únicos: {filtered_data['PAIS'].nunique()}\n"
    summary_text += f"- Áreas únicas: {filtered_data['AREA'].nunique()}\n"
    summary_text += f"- Cargos únicos: {filtered_data['CARGO'].nunique()}\n"
    summary_text += f"- Meses analizados: {len(selected_months)}\n"
    
    # Estadísticas de uso
    summary_text += f"- Uso mínimo de IA: {filtered_data['usos_ia'].min()}\n"
    summary_text += f"- Uso máximo de IA: {filtered_data['usos_ia'].max()}\n"
    summary_text += f"- Mediana de uso de IA: {filtered_data['usos_ia'].median():.1f}\n"
    summary_text += f"- Desviación estándar de uso: {filtered_data['usos_ia'].std():.1f}\n"
    
    return summary_text

# NUEVA FUNCIÓN: Mostrar sección de resumen con LLM
def show_llm_summary_section(filtered_data, selected_months, selected_countries, selected_areas, selected_cargo, filter_type):
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
        - Usos totales y promedios
        
        **📈 Análisis Detallado:**
        - Adopción por mes, país, área y cargo
        - Top 10 usuarios más activos
        - Estadísticas descriptivas
        - Tendencias y patrones identificados
        
        **🎯 Filtros Aplicados:**
        - Período temporal seleccionado
        - Países y áreas incluidos
        - Cargo específico (si aplica)
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
                selected_cargo, 
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

# NUEVA FUNCIÓN: Calcular rangos de ejes con margen del 10%
def calculate_axis_range(values, margin_percent=0.1):
    """
    Calcula el rango de ejes con margen especificado
    
    Args:
        values: Lista o array de valores numéricos
        margin_percent: Porcentaje de margen (0.1 = 10%)
    
    Returns:
        tuple: (valor_minimo_ajustado, valor_maximo_ajustado)
    """
    if len(values) == 0:
        return [0, 100]
    
    # Filtrar valores no nulos y convertir a numérico
    clean_values = [v for v in values if v is not None and not pd.isna(v)]
    
    if len(clean_values) == 0:
        return [0, 100]
    
    min_val = min(clean_values)
    max_val = max(clean_values)
    
    # Si todos los valores son iguales, crear un rango simétrico
    if min_val == max_val:
        if min_val == 0:
            return [-1, 1]
        else:
            margin = abs(min_val) * margin_percent
            return [min_val - margin, max_val + margin]
    
    # Calcular margen basado en el rango de datos
    data_range = max_val - min_val
    margin = data_range * margin_percent
    
    # Aplicar margen
    adjusted_min = min_val - margin
    adjusted_max = max_val + margin
    
    # Para valores que no pueden ser negativos (como porcentajes), ajustar el mínimo
    if min_val >= 0 and adjusted_min < 0:
        adjusted_min = max(0, min_val - (min_val * margin_percent))
    
    return [adjusted_min, adjusted_max]

# FUNCIÓN OPTIMIZADA: Aplicar rangos de ejes a gráficos
def apply_axis_ranges(fig, x_values=None, y_values=None, x_margin=0.1, y_margin=0.1):
    """
    Aplica rangos de ejes autoajustables a una figura de Plotly
    
    Args:
        fig: Figura de Plotly
        x_values: Valores del eje X (opcional)
        y_values: Valores del eje Y (opcional)
        x_margin: Margen para eje X (default 10%)
        y_margin: Margen para eje Y (default 10%)
    """
    # Aplicar rango al eje Y si se proporcionan valores
    if y_values is not None:
        y_range = calculate_axis_range(y_values, y_margin)
        fig.update_layout(yaxis=dict(range=y_range))
    
    # Aplicar rango al eje X si se proporcionan valores numéricos
    if x_values is not None and all(isinstance(v, (int, float)) for v in x_values if v is not None):
        x_range = calculate_axis_range(x_values, x_margin)
        fig.update_layout(xaxis=dict(range=x_range))
    
    return fig

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
        'show_adoption_by_area': len(selected_areas) > 1,
        'show_adoption_heatmap': len(selected_countries) > 1 or len(selected_areas) > 1,
        'show_usage_trend': len(selected_months) > 1,
        'show_usage_by_country': len(selected_countries) > 1,
        'show_usage_by_area': len(selected_areas) > 1,
        'show_usage_heatmap': len(selected_countries) > 1 or len(selected_areas) > 1
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
        'multiple_areas': "🏢 **Se requieren al menos 2 áreas** para mostrar la distribución entre áreas.",
        'multiple_dimensions': "🔥 **Se requieren al menos 2 países o 2 áreas** para generar el mapa de calor."
    }
    
    st.info(messages.get(requirement, "ℹ️ Condiciones insuficientes para mostrar este gráfico."))

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

# FUNCIÓN OPTIMIZADA: Filtrar meses por período
def filter_months_by_period(month_columns_sorted, selected_period):
    """
    Filtra los meses según el período seleccionado
    """
    if selected_period == "Todos los meses":
        return month_columns_sorted
    
    # Determinar cuántos meses tomar desde el final
    period_mapping = {
        "Últimos 3 meses": 3,
        "Últimos 6 meses": 6,
        "Últimos 9 meses": 9
    }
    
    if selected_period in period_mapping:
        num_months = period_mapping[selected_period]
        return month_columns_sorted[-num_months:] if len(month_columns_sorted) >= num_months else month_columns_sorted
    
    # NUEVA FUNCIONALIDAD: Mes anterior
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
        # Opciones de período predefinidas (AÑADIDA OPCIÓN "Mes anterior")
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
            help="Selecciona un período predefinido para filtrar los datos"
        )
        
        # Filtrar meses según el período seleccionado
        selected_months = filter_months_by_period(month_columns_sorted, selected_period)
        
        # Mostrar información del período seleccionado
        if selected_period == "Mes anterior":
            if len(selected_months) > 0:
                st.sidebar.info(f"📊 **Período seleccionado:** {selected_period}\n\n**Mes incluido:** {selected_months[0]}")
            else:
                st.sidebar.warning("⚠️ No hay suficientes meses para mostrar el mes anterior")
        elif selected_period != "Todos los meses":
            st.sidebar.info(f"📊 **Período seleccionado:** {selected_period}\n\n**Meses incluidos:** {len(selected_months)} meses")
        else:
            st.sidebar.info(f"📊 **Período seleccionado:** Todos los meses disponibles\n\n**Total de meses:** {len(selected_months)} meses")
    
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

# NUEVA FUNCIÓN: Crear filtros múltiples con checkboxes
def create_multiple_filters(df_melted):
    """
    Crea filtros múltiples con checkboxes para países y áreas
    
    Args:
        df_melted: DataFrame con los datos
    
    Returns:
        tuple: (selected_countries, selected_areas, selected_cargos)
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
    
    # Filtro múltiple por áreas
    st.sidebar.write("🏢 **Seleccionar Áreas:**")
    areas = sorted([str(x) for x in df_melted['AREA'].dropna().unique()])
    
    # Checkbox para seleccionar todas las áreas
    select_all_areas = st.sidebar.checkbox("Seleccionar todas las áreas", value=True)
    
    if select_all_areas:
        selected_areas = areas
    else:
        selected_areas = []
        for area in areas:
            if st.sidebar.checkbox(f"🏢 {area}", key=f"area_{area}"):
                selected_areas.append(area)
    
    st.sidebar.markdown("---")
    
    # Filtro simple por cargo (mantenemos el selectbox original)
    st.sidebar.write("💼 **Seleccionar Cargo:**")
    cargos = ['Todos'] + sorted([str(x) for x in df_melted['CARGO'].dropna().unique()])
    selected_cargo = st.sidebar.selectbox("💼 Cargo", cargos, key="cargo_filter")
    
    # Mostrar resumen de selección
    st.sidebar.markdown("---")
    st.sidebar.write("📊 **Resumen de Filtros:**")
    st.sidebar.write(f"• **Países:** {len(selected_countries)} seleccionados")
    st.sidebar.write(f"• **Áreas:** {len(selected_areas)} seleccionadas")
    st.sidebar.write(f"• **Cargo:** {selected_cargo}")
    
    return selected_countries, selected_areas, selected_cargo

# Función para cargar y procesar datos
@st.cache_data
def load_data(file):
    """
    Carga y procesa el archivo Excel con los datos de uso de IA
    """
    try:
        df = pd.read_excel(file)

        # Limpiar valores nulos en las columnas básicas
        df['NOMBRE'] = df['NOMBRE'].fillna('Sin Nombre')
        df['PAIS'] = df['PAIS'].fillna('Sin País')
        df['CARGO'] = df['CARGO'].fillna('Sin Cargo')
        df['AREA'] = df['AREA'].fillna('Sin Área')

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
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None, None, None

# FUNCIÓN OPTIMIZADA: Crear métricas principales en 2 filas con nuevas métricas de adopción
def create_metrics(df_melted, filtered_data, selected_months):
    """
    Calcula y muestra métricas principales del dashboard organizadas en 2 filas de 3 columnas cada una
    Incluye las nuevas métricas de adopción: % Acumulado Adopción SAI y % Promedio Adopción SAI
    """
    # PRIMERA FILA - 3 métricas principales
    col1, col2, col3 = st.columns(3)

    with col1:
        # Total Profesionales Elegibles
        total_eligible_professionals = filtered_data['NOMBRE'].nunique()
        st.metric("👥 Total Profesionales Elegibles", total_eligible_professionals)

    with col2:
        # Total de Usuarios Activos (usuarios con al menos 1 uso de IA)
        active_users = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
        st.metric("🚀 Total Usuarios Activos", active_users)

    with col3:
        # Total de usos de IA
        total_usage = int(filtered_data['usos_ia'].sum())
        st.metric("📊 Usos Totales IA", f"{total_usage:,}")

    # SEGUNDA FILA - 3 métricas adicionales (OPTIMIZADAS)
    col4, col5, col6 = st.columns(3)

    with col4:
        # Promedio mensual
        avg_usage = filtered_data['usos_ia'].mean()
        st.metric("📈 Promedio Mensual", f"{avg_usage:.1f}")

    with col5:
        # NUEVA MÉTRICA: % Acumulado Adopción SAI (antes era % Adopción SAI)
        users_with_usage = filtered_data[filtered_data['usos_ia'] > 0]['NOMBRE'].nunique()
        total_unique_users = filtered_data['NOMBRE'].nunique()
        
        if total_unique_users > 0:
            cumulative_adoption_rate = (users_with_usage / total_unique_users) * 100
        else:
            cumulative_adoption_rate = 0
            
        st.metric("🎯 % Acumulado Adopción SAI", f"{cumulative_adoption_rate:.1f}%")

    with col6:
        # NUEVA MÉTRICA: % Promedio Adopción SAI
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

# NUEVA FUNCIÓN: Gráfico de distribución de adopción por área
def create_adoption_distribution_by_area(filtered_data):
    """
    Crea gráfico de distribución de adopción por área (gráfico de dona)
    """
    # Calcular adopción por área
    area_adoption = []
    
    for area in filtered_data['AREA'].unique():
        area_data = filtered_data[filtered_data['AREA'] == area]
        total_users = area_data['NOMBRE'].nunique()
        active_users = area_data[area_data['usos_ia'] > 0]['NOMBRE'].nunique()
        
        adoption_rate = (active_users / total_users) * 100 if total_users > 0 else 0
        
        area_adoption.append({
            'Área': area,
            'Total_Usuarios': total_users,
            'Usuarios_Activos': active_users,
            'Porcentaje_Adopcion': adoption_rate
        })
    
    adoption_df = pd.DataFrame(area_adoption)
    adoption_df = adoption_df.sort_values('Porcentaje_Adopcion', ascending=False)
    
    # Crear gráfico de dona
    fig = px.pie(
        adoption_df,
        values='Porcentaje_Adopcion',
        names='Área',
        title='🎯 Distribución de Adopción SAI por Área (%)',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Personalizar el gráfico
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>' +
                      'Adopción: %{value:.1f}%<br>' +
                      'Total Usuarios: %{customdata[0]}<br>' +
                      'Usuarios Activos: %{customdata[1]}<extra></extra>',
        customdata=adoption_df[['Total_Usuarios', 'Usuarios_Activos']].values
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        )
    )
    
    return fig

# FUNCIÓN OPTIMIZADA: Gráfico de adopción SAI vs País con ejes autoajustables
def create_adoption_by_country(filtered_data):
    """
    Crea gráfico de % de adopción de SAI por país con ejes autoajustables
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
    
    # APLICAR EJES AUTOAJUSTABLES
    fig = apply_axis_ranges(fig, y_values=adoption_df['Porcentaje_Adopcion'].tolist())
    
    fig.update_layout(
        xaxis_title="País",
        yaxis_title="% Adopción SAI",
        xaxis_tickangle=-45
    )
    
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>' +
                      'Adopción: %{y:.1f}%<br>' +
                      'Total Usuarios: %{customdata[0]}<br>' +
                      'Usuarios Activos: %{customdata[1]}<extra></extra>'
    )
    
    return fig

# FUNCIÓN OPTIMIZADA: Gráfico de adopción SAI por Cargo con ejes autoajustables
def create_adoption_by_cargo(filtered_data):
    """
    Crea gráfico de % de adopción de SAI por cargo con ejes autoajustables
    """
    # Calcular adopción por cargo
    cargo_adoption = []
    
    for cargo in filtered_data['CARGO'].unique():
        cargo_data = filtered_data[filtered_data['CARGO'] == cargo]
        total_users = cargo_data['NOMBRE'].nunique()
        active_users = cargo_data[cargo_data['usos_ia'] > 0]['NOMBRE'].nunique()
        
        adoption_rate = (active_users / total_users) * 100 if total_users > 0 else 0
        
        cargo_adoption.append({
            'Cargo': cargo,
            'Total_Usuarios': total_users,
            'Usuarios_Activos': active_users,
            'Porcentaje_Adopcion': adoption_rate
        })
    
    adoption_df = pd.DataFrame(cargo_adoption)
    adoption_df = adoption_df.sort_values('Porcentaje_Adopcion', ascending=True)
    
    # Crear gráfico de barras horizontales
    fig = px.bar(
        adoption_df,
        x='Porcentaje_Adopcion',
        y='Cargo',
        title='💼 % Adopción SAI por Cargo',
        color='Porcentaje_Adopcion',
        color_continuous_scale='plasma',
        orientation='h',
        hover_data=['Total_Usuarios', 'Usuarios_Activos']
    )
    
    # APLICAR EJES AUTOAJUSTABLES
    fig = apply_axis_ranges(fig, x_values=adoption_df['Porcentaje_Adopcion'].tolist())
    
    fig.update_layout(
        xaxis_title="% Adopción SAI",
        yaxis_title="Cargo"
    )
    
    fig.update_traces(
        hovertemplate='<b>%{y}</b><br>' +
                      'Adopción: %{x:.1f}%<br>' +
                      'Total Usuarios: %{customdata[0]}<br>' +
                      'Usuarios Activos: %{customdata[1]}<extra></extra>'
    )
    
    return fig

# FUNCIÓN OPTIMIZADA: Mapa de calor de adopción SAI por País y Área con ejes autoajustables
def create_adoption_heatmap(filtered_data):
    """
    Crea mapa de calor de % de adopción de SAI por país y área con ejes autoajustables
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
    
    # Crear pivot table para el heatmap
    heatmap_pivot = adoption_df.pivot(
        index='País', 
        columns='Área', 
        values='Porcentaje_Adopcion'
    ).fillna(0)
    
    # Obtener valores para calcular rango de colores
    all_values = heatmap_pivot.values.flatten()
    all_values = [v for v in all_values if not pd.isna(v)]
    
    # Calcular rango de colores con margen
    if all_values:
        color_range = calculate_axis_range(all_values)
        zmin, zmax = color_range
    else:
        zmin, zmax = 0, 100
    
    # Crear heatmap
    fig = px.imshow(
        heatmap_pivot,
        title='🔥 Mapa de Calor: % Adopción SAI por País y Área',
        color_continuous_scale='RdYlBu_r',
        aspect='auto',
        labels=dict(color="% Adopción SAI"),
        zmin=zmin,
        zmax=zmax
    )
    
    fig.update_layout(
        xaxis_title="Área",
        yaxis_title="País"
    )
    
    # Añadir valores de texto en cada celda
    fig.update_traces(
        text=heatmap_pivot.round(1),
        texttemplate="%{text}%",
        textfont={"size": 10}
    )
    
    return fig

# FUNCIÓN OPTIMIZADA: Gráfico de % Adopción vs Tiempo con ejes autoajustables
def create_adoption_trend(filtered_data, selected_months):
    """
    Crea gráfico de tendencia de % de adopción a lo largo del tiempo con ejes autoajustables
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
    
    # APLICAR EJES AUTOAJUSTABLES
    fig = apply_axis_ranges(fig, y_values=adoption_df['Porcentaje_Adopcion'].tolist())
    
    fig.update_layout(
        title='📈 Evolución del % de Adopción de SAI por Mes',
        xaxis_title='Mes',
        yaxis_title='Porcentaje de Adopción (%)',
        hovermode='x unified',
        showlegend=True,
        height=400
    )
    
    return fig

# FUNCIÓN OPTIMIZADA: Gráfico de tendencia temporal con ejes autoajustables
def create_time_trend(filtered_data, month_columns_sorted):
    """
    Crea gráfico de tendencia temporal de uso de IA con meses ordenados y ejes autoajustables
    """
    monthly_usage = filtered_data.groupby('Mes')['usos_ia'].sum().reset_index()
    
    # Crear un mapeo de orden para los meses
    month_order = {month: i for i, month in enumerate(month_columns_sorted)}
    monthly_usage['order'] = monthly_usage['Mes'].map(month_order)
    monthly_usage = monthly_usage.sort_values('order')

    fig = px.line(
        monthly_usage,
        x='Mes',
        y='usos_ia',
        title='📈 Tendencia de Uso de IA por Mes',
        markers=True
    )

    # APLICAR EJES AUTOAJUSTABLES
    fig = apply_axis_ranges(fig, y_values=monthly_usage['usos_ia'].tolist())

    fig.update_layout(
        xaxis_title="Mes",
        yaxis_title="Usos de IA",
        hovermode='x unified'
    )

    return fig

# FUNCIÓN OPTIMIZADA: Gráfico por país con ejes autoajustables
def create_country_analysis(filtered_data):
    """
    Crea análisis por país con gráfico de barras y ejes autoajustables
    """
    country_data = filtered_data.groupby('PAIS')['usos_ia'].sum().reset_index()
    country_data = country_data.sort_values('usos_ia', ascending=False)

    fig = px.bar(
        country_data,
        x='PAIS',
        y='usos_ia',
        title='🌎 Uso de IA por País',
        color='usos_ia',
        color_continuous_scale='viridis'
    )

    # APLICAR EJES AUTOAJUSTABLES
    fig = apply_axis_ranges(fig, y_values=country_data['usos_ia'].tolist())

    fig.update_layout(
        xaxis_title="País",
        yaxis_title="Usos de IA",
        xaxis_tickangle=-45
    )

    return fig

# FUNCIÓN OPTIMIZADA: Gráfico por área (mantiene formato de dona)
def create_area_analysis(filtered_data):
    """
    Crea análisis por área con gráfico de dona (sin cambios en ejes)
    """
    area_data = filtered_data.groupby('AREA')['usos_ia'].sum().reset_index()

    fig = px.pie(
        area_data,
        values='usos_ia',
        names='AREA',
        title='🏢 Distribución de Uso por Área',
        hole=0.4
    )

    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig

# FUNCIÓN OPTIMIZADA: Gráfico por cargo con ejes autoajustables
def create_cargo_analysis(filtered_data):
    """
    Crea análisis por cargo con gráfico de barras horizontales y ejes autoajustables
    """
    cargo_data = filtered_data.groupby('CARGO')['usos_ia'].sum().reset_index()
    cargo_data = cargo_data.sort_values('usos_ia', ascending=True)

    fig = px.bar(
        cargo_data,
        x='usos_ia',
        y='CARGO',
        title='💼 Uso de IA por Cargo',
        color='usos_ia',
        color_continuous_scale='plasma',
        orientation='h'
    )

    # APLICAR EJES AUTOAJUSTABLES
    fig = apply_axis_ranges(fig, x_values=cargo_data['usos_ia'].tolist())

    fig.update_layout(
        xaxis_title="Usos de IA",
        yaxis_title="Cargo"
    )

    return fig

# FUNCIÓN OPTIMIZADA: Heatmap de uso por país y área con ejes autoajustables
def create_heatmap(filtered_data):
    """
    Crea heatmap de uso de IA por país y área con ejes autoajustables
    """
    heatmap_data = filtered_data.groupby(['PAIS', 'AREA'])['usos_ia'].sum().reset_index()
    heatmap_pivot = heatmap_data.pivot(index='PAIS', columns='AREA', values='usos_ia').fillna(0)

    # Obtener valores para calcular rango de colores
    all_values = heatmap_pivot.values.flatten()
    all_values = [v for v in all_values if not pd.isna(v)]
    
    # Calcular rango de colores con margen
    if all_values:
        color_range = calculate_axis_range(all_values)
        zmin, zmax = color_range
    else:
        zmin, zmax = 0, 100

    fig = px.imshow(
        heatmap_pivot,
        title='🔥 Mapa de Calor: Uso por País y Área',
        color_continuous_scale='RdYlBu_r',
        aspect='auto',
        zmin=zmin,
        zmax=zmax
    )

    fig.update_layout(
        xaxis_title="Área",
        yaxis_title="País"
    )

    return fig

# Función para top usuarios (sin cambios)
def create_top_users(filtered_data):
    """
    Muestra tabla de top usuarios por uso de IA
    """
    top_users = filtered_data.groupby(['NOMBRE', 'PAIS', 'CARGO', 'AREA'])['usos_ia'].sum().reset_index()
    top_users = top_users.sort_values('usos_ia', ascending=False).head(10)

    return top_users

# NUEVA FUNCIÓN: Crear tabla de análisis de adopción detallado
def create_adoption_analysis_table(filtered_data, month_columns_sorted, selected_months):
    """
    Crea tabla detallada de análisis de adopción por mes
    """
    adoption_data = []
    
    for month in month_columns_sorted:
        if month in selected_months:
            month_data = filtered_data[filtered_data['Mes'] == month]
            total_users = month_data['NOMBRE'].nunique()
            users_with_usage = month_data[month_data['usos_ia'] > 0]['NOMBRE'].nunique()
            users_without_usage = total_users - users_with_usage
            
            adoption_percentage = (users_with_usage / total_users) * 100 if total_users > 0 else 0
            
            adoption_data.append({
                'Mes': month,
                'Total Usuarios': total_users,
                'Usuarios Activos': users_with_usage,
                'Usuarios Inactivos': users_without_usage,
                '% Adopción': round(adoption_percentage, 1)
            })
    
    return pd.DataFrame(adoption_data)

# ==========================================
# NUEVAS FUNCIONES PARA RANKINGS
# ==========================================

def create_top_5_users_ranking(filtered_data):
    """
    Crea tabla de ranking con los top 5 usuarios que más usan SAI en el período filtrado
    
    Args:
        filtered_data: DataFrame con datos filtrados
    
    Returns:
        pd.DataFrame: DataFrame con el ranking de top 5 usuarios
    """
    # Agrupar por usuario y sumar todos los usos de SAI
    user_ranking = filtered_data.groupby(['NOMBRE', 'PAIS', 'CARGO', 'AREA']).agg({
        'usos_ia': 'sum'
    }).reset_index()
    
    # Ordenar por usos de IA de mayor a menor y tomar top 5
    user_ranking = user_ranking.sort_values('usos_ia', ascending=False).head(5)
    
    # Agregar columna de posición
    user_ranking.insert(0, 'Posición', range(1, len(user_ranking) + 1))
    
    # Renombrar columnas para mejor presentación
    user_ranking = user_ranking.rename(columns={
        'NOMBRE': 'Nombre',
        'PAIS': 'País',
        'CARGO': 'Cargo',
        'AREA': 'Área',
        'usos_ia': 'Total Usos SAI'
    })
    
    return user_ranking

def create_country_ranking(filtered_data):
    """
    Crea tabla de ranking por país basado en el total de usos de SAI
    
    Args:
        filtered_data: DataFrame con datos filtrados
    
    Returns:
        pd.DataFrame: DataFrame con el ranking por países
    """
    # Agrupar por país y calcular métricas
    country_ranking = filtered_data.groupby('PAIS').agg({
        'NOMBRE': 'nunique',  # Usuarios únicos
        'usos_ia': 'sum'      # Total de usos
    }).reset_index()
    
    # Calcular usuarios activos por país
    active_users_by_country = filtered_data[filtered_data['usos_ia'] > 0].groupby('PAIS')['NOMBRE'].nunique().reset_index()
    active_users_by_country = active_users_by_country.rename(columns={'NOMBRE': 'usuarios_activos'})
    
    # Unir con el ranking principal
    country_ranking = country_ranking.merge(active_users_by_country, on='PAIS', how='left')
    country_ranking['usuarios_activos'] = country_ranking['usuarios_activos'].fillna(0)
    
    # Calcular porcentaje de adopción por país
    country_ranking['porcentaje_adopcion'] = (
        country_ranking['usuarios_activos'] / country_ranking['NOMBRE'] * 100
    ).round(1)
    
    # Calcular promedio de usos por usuario activo
    country_ranking['promedio_usos_por_usuario'] = (
        country_ranking['usos_ia'] / country_ranking['usuarios_activos']
    ).fillna(0).round(1)
    
    # Ordenar por total de usos de IA de mayor a menor
    country_ranking = country_ranking.sort_values('usos_ia', ascending=False)
    
    # Agregar columna de posición
    country_ranking.insert(0, 'Posición', range(1, len(country_ranking) + 1))
    
    # Renombrar columnas para mejor presentación
    country_ranking = country_ranking.rename(columns={
        'PAIS': 'País',
        'NOMBRE': 'Total Usuarios',
        'usos_ia': 'Total Usos SAI',
        'usuarios_activos': 'Usuarios Activos',
        'porcentaje_adopcion': '% Adopción',
        'promedio_usos_por_usuario': 'Promedio Usos/Usuario Activo'
    })
    
    return country_ranking

def show_rankings_section(filtered_data):
    """
    Muestra la sección completa de rankings con tablas y visualizaciones
    
    Args:
        filtered_data: DataFrame con datos filtrados
    """
    st.subheader("🏆 Rankings y Clasificaciones")
    st.markdown("Análisis de los mejores performers en el uso de SAI durante el período seleccionado.")
    
    # Crear dos columnas para mostrar los rankings lado a lado
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👑 Top 5 Usuarios SAI")
        st.markdown("*Los 5 usuarios con mayor uso de SAI en el período filtrado*")
        
        # Crear y mostrar tabla de top 5 usuarios
        top_5_users = create_top_5_users_ranking(filtered_data)
        
        if len(top_5_users) > 0:
            # Aplicar estilo a la tabla
            st.dataframe(
                top_5_users,
                use_container_width=True,
                hide_index=True
            )
            
            # Botón de descarga para top 5 usuarios
            csv_top_5 = top_5_users.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Top 5 Usuarios",
                data=csv_top_5,
                file_name=f'top_5_usuarios_sai_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                key="download_top_5_users"
            )
            
            # Mostrar insights del top 5
            if len(top_5_users) > 0:
                top_user = top_5_users.iloc[0]
                total_top_5_usage = top_5_users['Total Usos SAI'].sum()
                st.info(f"""
                **🎯 Insights del Top 5:**
                - **Líder:** {top_user['Nombre']} ({top_user['País']}) con {top_user['Total Usos SAI']} usos
                - **Total combinado:** {total_top_5_usage:,} usos de SAI
                - **Promedio Top 5:** {total_top_5_usage/len(top_5_users):.1f} usos por usuario
                """)
        else:
            st.warning("⚠️ No hay datos suficientes para generar el ranking de usuarios.")
    
    with col2:
        st.markdown("### 🌍 Ranking por Países")
        st.markdown("*Clasificación de países por desempeño en uso de SAI*")
        
        # Crear y mostrar tabla de ranking por países
        country_ranking = create_country_ranking(filtered_data)
        
        if len(country_ranking) > 0:
            # Aplicar estilo a la tabla
            st.dataframe(
                country_ranking,
                use_container_width=True,
                hide_index=True
            )
            
            # Botón de descarga para ranking de países
            csv_countries = country_ranking.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Ranking Países",
                data=csv_countries,
                file_name=f'ranking_paises_sai_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                key="download_country_ranking"
            )
            
            # Mostrar insights del ranking de países
            if len(country_ranking) > 0:
                top_country = country_ranking.iloc[0]
                total_countries = len(country_ranking)
                total_usage_all = country_ranking['Total Usos SAI'].sum()
                st.info(f"""
                **🎯 Insights por País:**
                - **País líder:** {top_country['País']} con {top_country['Total Usos SAI']:,} usos
                - **Total países:** {total_countries}
                - **Uso total combinado:** {total_usage_all:,} usos de SAI
                - **Mejor adopción:** {country_ranking.loc[country_ranking['% Adopción'].idxmax(), 'País']} ({country_ranking['% Adopción'].max():.1f}%)
                """)
        else:
            st.warning("⚠️ No hay datos suficientes para generar el ranking de países.")
    
    # Sección adicional: Gráficos de rankings
    st.markdown("---")
    st.markdown("### 📊 Visualizaciones de Rankings")
    
    # Crear pestañas para diferentes visualizaciones
    tab_users, tab_countries = st.tabs(["👑 Gráfico Top Usuarios", "🌍 Gráfico Países"])
    
    with tab_users:
        if len(top_5_users) > 0:
            # Gráfico de barras para top 5 usuarios
            fig_users = px.bar(
                top_5_users,
                x='Nombre',
                y='Total Usos SAI',
                title='🏆 Top 5 Usuarios por Uso de SAI',
                color='Total Usos SAI',
                color_continuous_scale='viridis',
                text='Total Usos SAI'
            )
            
            fig_users.update_traces(texttemplate='%{text}', textposition='outside')
            fig_users.update_layout(
                xaxis_title="Usuario",
                yaxis_title="Total Usos SAI",
                xaxis_tickangle=-45,
                showlegend=False
            )
            
            # Aplicar ejes autoajustables
            fig_users = apply_axis_ranges(fig_users, y_values=top_5_users['Total Usos SAI'].tolist())
            
            st.plotly_chart(fig_users, use_container_width=True)
        else:
            st.info("📊 No hay suficientes datos para mostrar el gráfico de top usuarios.")
    
    with tab_countries:
        if len(country_ranking) > 0:
            # Gráfico de barras para ranking de países
            fig_countries = px.bar(
                country_ranking.head(10),  # Mostrar solo top 10 países
                x='País',
                y='Total Usos SAI',
                title='🌍 Ranking de Países por Uso Total de SAI',
                color='% Adopción',
                color_continuous_scale='plasma',
                hover_data=['Total Usuarios', 'Usuarios Activos', '% Adopción']
            )
            
            fig_countries.update_layout(
                xaxis_title="País",
                yaxis_title="Total Usos SAI",
                xaxis_tickangle=-45
            )
            
            # Aplicar ejes autoajustables
            fig_countries = apply_axis_ranges(fig_countries, y_values=country_ranking['Total Usos SAI'].tolist())
            
            st.plotly_chart(fig_countries, use_container_width=True)
        else:
            st.info("📊 No hay suficientes datos para mostrar el gráfico de países.")

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

# Aplicación principal
def main():
    # Título principal
    st.title("🤖 Dashboard de Análisis de SAI - Áreas internas")
    st.markdown("---")

    # Sidebar para carga de archivo y filtros
    st.sidebar.header("📁 Configuración")

    # Carga de archivo
    uploaded_file = st.sidebar.file_uploader(
        "Cargar archivo Excel",
        type=['xlsx', 'xls'],
        help="Sube tu archivo Excel con las columnas: NOMBRE, PAIS, CARGO, AREA y meses"
    )

    if uploaded_file is not None:
        # Cargar datos
        df_original, df_melted, month_columns_sorted = load_data(uploaded_file)

        if df_melted is not None:
            # Filtros en sidebar
            st.sidebar.header("🔍 Filtros")

            # FILTROS DINÁMICOS OPTIMIZADOS: Crear filtros temporales dinámicos
            selected_months, filter_type = create_dynamic_filters(month_columns_sorted)

            # Separador visual
            st.sidebar.markdown("---")

            # NUEVOS FILTROS MÚLTIPLES: Crear filtros múltiples con checkboxes
            selected_countries, selected_areas, selected_cargo = create_multiple_filters(df_melted)

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

            # Filtrar por cargo (si no es "Todos")
            if selected_cargo != 'Todos':
                filtered_data = filtered_data[filtered_data['CARGO'] == selected_cargo]

            # Filtrar por meses seleccionados
            filtered_data = filtered_data[filtered_data['Mes'].isin(selected_months)]

            # Mostrar información del filtro aplicado
            st.info(f"📊 **Filtro temporal:** {filter_type} | **Meses:** {len(selected_months)} | **Países:** {len(selected_countries)} | **Áreas:** {len(selected_areas)}")

            # SECCIÓN OPTIMIZADA: Mostrar métricas principales en 2 filas (ACTUALIZADA)
            st.header("📊 Métricas Principales")
            create_metrics(df_melted, filtered_data, selected_months)
            st.markdown("---")

            # ==========================================
            # NUEVA SECCIÓN: RESUMEN INTELIGENTE CON LLM
            # ==========================================
            show_llm_summary_section(filtered_data, selected_months, selected_countries, selected_areas, selected_cargo, filter_type)
            st.markdown("---")

            # ==========================================
            # NUEVA SECCIÓN: PESTAÑAS PRINCIPALES CON VALIDACIONES
            # ==========================================
            
            # Crear pestañas principales para separar análisis de Adopción y Uso
            tab_adopcion, tab_uso = st.tabs(["🎯 Análisis de Adopción SAI", "📊 Análisis de Uso SAI"])
            
            # ==========================================
            # PESTAÑA 1: ANÁLISIS DE ADOPCIÓN SAI CON VALIDACIONES
            # ==========================================
            with tab_adopcion:
                st.header("🎯 Análisis de Adopción SAI")
                
                # Gráfico 1: Evolución de Adopción (VALIDACIÓN: solo si hay más de 1 mes)
                st.subheader("📈 Evolución del % de Adopción por Mes")
                if chart_conditions['show_adoption_trend']:
                    fig_adoption_trend = create_adoption_trend(filtered_data, selected_months)
                    st.plotly_chart(fig_adoption_trend, use_container_width=True)
                else:
                    show_chart_requirement_message("adoption_trend", "multiple_months")
                st.markdown("---")
                
                # Gráfico 2: Adopción por País (VALIDACIÓN: solo si hay más de 1 país)
                st.subheader("🌎 % Adopción SAI por País")
                if chart_conditions['show_adoption_by_country']:
                    fig_adoption_country = create_adoption_by_country(filtered_data)
                    st.plotly_chart(fig_adoption_country, use_container_width=True)
                else:
                    show_chart_requirement_message("adoption_by_country", "multiple_countries")
                st.markdown("---")
                
                # Gráfico 3: Adopción por Cargo (sin validación - siempre se muestra)
                st.subheader("💼 % Adopción SAI por Cargo")
                fig_adoption_cargo = create_adoption_by_cargo(filtered_data)
                st.plotly_chart(fig_adoption_cargo, use_container_width=True)
                st.markdown("---")
                
                # Gráfico 4: Distribución de Adopción por Área (VALIDACIÓN: solo si hay más de 1 área)
                st.subheader("🎯 Distribución de Adopción SAI por Área")
                if chart_conditions['show_adoption_by_area']:
                    fig_adoption_distribution = create_adoption_distribution_by_area(filtered_data)
                    st.plotly_chart(fig_adoption_distribution, use_container_width=True)
                else:
                    show_chart_requirement_message("adoption_by_area", "multiple_areas")
                st.markdown("---")
                
                # Gráfico 5: Mapa de Calor de Adopción (VALIDACIÓN: solo si hay más de 1 país o más de 1 área)
                st.subheader("🔥 Mapa de Calor: % Adopción SAI por País y Área")
                if chart_conditions['show_adoption_heatmap']:
                    fig_adoption_heatmap = create_adoption_heatmap(filtered_data)
                    st.plotly_chart(fig_adoption_heatmap, use_container_width=True)
                else:
                    show_chart_requirement_message("adoption_heatmap", "multiple_dimensions")
                st.markdown("---")
                
                # Tabla: Análisis Detallado de Adopción (siempre se muestra)
                st.subheader("📋 Tabla de Análisis de Adopción por Mes")
                adoption_table = create_adoption_analysis_table(filtered_data, month_columns_sorted, selected_months)
                st.dataframe(adoption_table, use_container_width=True)
                
                # Botón de descarga para datos de adopción
                csv_adoption = adoption_table.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar datos de adopción",
                    data=csv_adoption,
                    file_name='analisis_adopcion_sai.csv',
                    mime='text/csv'
                )
            
            # ==========================================
            # PESTAÑA 2: ANÁLISIS DE USO SAI CON VALIDACIONES
            # ==========================================
            with tab_uso:
                st.header("📊 Análisis de Uso SAI")
                
                # Gráfico 1: Tendencia Temporal de Uso (VALIDACIÓN: solo si hay más de 1 mes)
                st.subheader("📈 Tendencia de Uso de IA por Mes")
                if chart_conditions['show_usage_trend']:
                    fig_time_trend = create_time_trend(filtered_data, month_columns_sorted)
                    st.plotly_chart(fig_time_trend, use_container_width=True)
                else:
                    show_chart_requirement_message("usage_trend", "multiple_months")
                st.markdown("---")
                
                # Gráfico 2: Uso por País (VALIDACIÓN: solo si hay más de 1 país)
                st.subheader("🌎 Uso de IA por País")
                if chart_conditions['show_usage_by_country']:
                    fig_country = create_country_analysis(filtered_data)
                    st.plotly_chart(fig_country, use_container_width=True)
                else:
                    show_chart_requirement_message("usage_by_country", "multiple_countries")
                st.markdown("---")
                
                # Gráfico 3: Uso por Área (VALIDACIÓN: solo si hay más de 1 área)
                st.subheader("🏢 Distribución de Uso por Área")
                if chart_conditions['show_usage_by_area']:
                    fig_area = create_area_analysis(filtered_data)
                    st.plotly_chart(fig_area, use_container_width=True)
                else:
                    show_chart_requirement_message("usage_by_area", "multiple_areas")
                st.markdown("---")
                
                # Gráfico 4: Uso por Cargo (sin validación - siempre se muestra)
                st.subheader("💼 Uso de IA por Cargo")
                fig_cargo = create_cargo_analysis(filtered_data)
                st.plotly_chart(fig_cargo, use_container_width=True)
                st.markdown("---")
                
                # Gráfico 5: Mapa de Calor de Uso (VALIDACIÓN: solo si hay más de 1 país o más de 1 área)
                st.subheader("🔥 Mapa de Calor: Uso por País y Área")
                if chart_conditions['show_usage_heatmap']:
                    fig_heatmap = create_heatmap(filtered_data)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                else:
                    show_chart_requirement_message("usage_heatmap", "multiple_dimensions")
                st.markdown("---")
                
                # Tabla: Top Usuarios (siempre se muestra)
                st.subheader("🏆 Top 10 Usuarios por Uso de IA")
                top_users = create_top_users(filtered_data)
                st.dataframe(top_users, use_container_width=True)
                
                # Botón de descarga para top usuarios
                csv_top_users = top_users.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar top usuarios",
                    data=csv_top_users,
                    file_name='top_usuarios_sai.csv',
                    mime='text/csv'
                )

            # ==========================================
            # SECCIÓN ADICIONAL: ANÁLISIS DETALLADO (OPTIMIZADA CON NUEVA PESTAÑA DE RANKINGS)
            # ==========================================
            st.markdown("---")
            st.header("📋 Análisis Detallado Adicional")

            # PESTAÑAS ACTUALIZADAS: Agregamos la nueva pestaña de Rankings
            tab1, tab2, tab3, tab4 = st.tabs([
                "📄 Datos Filtrados", 
                "📈 Resumen Estadístico", 
                "📊 Estadísticas Generales",
                "🏆 Rankings"  # NUEVA PESTAÑA
            ])

            with tab1:
                st.subheader("📄 Datos Filtrados Completos")
                st.dataframe(filtered_data, use_container_width=True)

                # Botón de descarga
                csv = filtered_data.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar datos filtrados completos",
                    data=csv,
                    file_name='datos_filtrados_ia_completos.csv',
                    mime='text/csv'
                )

            with tab2:
                st.subheader("📈 Resumen Estadístico por Dimensiones")

                # Estadísticas por País
                st.write("**📍 Estadísticas por País:**")
                country_stats = filtered_data.groupby('PAIS').agg({
                    'NOMBRE': 'nunique',
                    'usos_ia': ['sum', 'mean', 'std']
                }).round(2)
                
                country_stats.columns = [
                    'Total de registros de personas',
                    'Total de usos de SAI', 
                    'Media de Uso SAI',
                    'Desviación Estándar de Uso SAI'
                ]
                
                country_stats['Desviación Estándar de Uso SAI'] = country_stats['Desviación Estándar de Uso SAI'].fillna(0)
                st.dataframe(country_stats, use_container_width=True)
                
                st.markdown("---")
                
                # Estadísticas por Área
                st.write("**🏢 Estadísticas por Área:**")
                area_stats = filtered_data.groupby('AREA').agg({
                    'NOMBRE': 'nunique',
                    'usos_ia': ['sum', 'mean', 'std']
                }).round(2)
                
                area_stats.columns = [
                    'Total de registros de personas',
                    'Total de usos de SAI', 
                    'Media de Uso SAI',
                    'Desviación Estándar de Uso SAI'
                ]
                
                area_stats['Desviación Estándar de Uso SAI'] = area_stats['Desviación Estándar de Uso SAI'].fillna(0)
                st.dataframe(area_stats, use_container_width=True)
                
                st.markdown("---")
                
                # Estadísticas por Cargo
                st.write("**💼 Estadísticas por Cargo:**")
                cargo_stats = filtered_data.groupby('CARGO').agg({
                    'NOMBRE': 'nunique',
                    'usos_ia': ['sum', 'mean', 'std']
                }).round(2)
                
                cargo_stats.columns = [
                    'Total de registros de personas',
                    'Total de usos de SAI', 
                    'Media de Uso SAI',
                    'Desviación Estándar de Uso SAI'
                ]
                
                cargo_stats['Desviación Estándar de Uso SAI'] = cargo_stats['Desviación Estándar de Uso SAI'].fillna(0)
                st.dataframe(cargo_stats, use_container_width=True)

            with tab3:
                st.subheader("📊 Estadísticas Generales del Dataset")
                
                # Información general
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📊 Total de Registros", len(filtered_data))
                    st.metric("👥 Usuarios Únicos", filtered_data['NOMBRE'].nunique())
                
                with col2:
                    st.metric("🌍 Países Únicos", filtered_data['PAIS'].nunique())
                    st.metric("🏢 Áreas Únicas", filtered_data['AREA'].nunique())
                
                with col3:
                    st.metric("💼 Cargos Únicos", filtered_data['CARGO'].nunique())
                    st.metric("📅 Meses Analizados", len(selected_months))

            # ==========================================
            # NUEVA PESTAÑA: RANKINGS
            # ==========================================
            with tab4:
                show_rankings_section(filtered_data)

    else:
        # Mensaje de bienvenida
        st.info("👆 Por favor, carga tu archivo Excel en la barra lateral para comenzar el análisis.")

        # Mostrar ejemplo de estructura de datos
        st.subheader("📋 Estructura de datos esperada:")
        example_data = {
            'NOMBRE': ['Juan Pérez', 'María García', 'Carlos López'],
            'PAIS': ['México', 'España', 'Argentina'],
            'CARGO': ['Analista', 'Gerente', 'Coordinador'],
            'AREA': ['Marketing', 'IT', 'Ventas'],
            'Sep-24': [45, 32, 28],
            'Oct-24': [52, 38, 31],
            'Nov-24': [48, 41, 35]
        }
        st.dataframe(pd.DataFrame(example_data))

if __name__ == "__main__":

    main()
