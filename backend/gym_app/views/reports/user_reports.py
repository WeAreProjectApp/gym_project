"""
User-related Excel report generators.
"""
import datetime
import pandas as pd
from django.db.models import Count, Exists, OuterRef
from django.utils import timezone

from gym_app.models import Process, Case, User, ActivityFeed
from gym_app.views.reports import _get_user_id

ROLE_DISPLAY_MAP = {
    'client': 'Cliente',
    'lawyer': 'Abogado',
    'corporate_client': 'Cliente Corporativo',
    'basic': 'Básico',
}

MAX_LAWYERS_WORKLOAD_QUERIES = 6


def generate_registered_users_report(
    response, start_date, end_datetime,
    filter_role=None, filter_profile_status=None, filter_document_type=None
):
    """
    Generate report of registered users with detailed information.

    Columns:
    - Email, Nombre, Apellido, Rol, Tipo de Documento, Identificación,
      Contacto, Perfil Completo, Activo, Abogado GYM, Fecha de Registro

    Optional filters:
    - filter_role: 'client' | 'lawyer' | 'corporate_client' | 'basic'
    - filter_profile_status: 'complete' | 'incomplete'
    - filter_document_type: 'NIT' | 'CC' | 'NUIP' | 'EIN'
    """
    # Get users created in the date range
    users = User.objects.filter(created_at__range=[start_date, end_datetime]).only(
        'email', 'first_name', 'last_name', 'role', 'document_type',
        'identification', 'contact', 'is_profile_completed',
        'is_active', 'is_gym_lawyer', 'created_at',
    )

    # Apply optional filters
    if filter_role:
        users = users.filter(role=filter_role)
    if filter_profile_status == 'complete':
        users = users.filter(is_profile_completed=True)
    elif filter_profile_status == 'incomplete':
        users = users.filter(is_profile_completed=False)
    if filter_document_type:
        users = users.filter(document_type=filter_document_type)

    # Prepare data for Excel
    data = []
    for user in users:
        data.append({
            'Email': user.email,
            'Nombre': user.first_name or "",
            'Apellido': user.last_name or "",
            'Rol': ROLE_DISPLAY_MAP.get(user.role, user.role),
            'Tipo de Documento': user.document_type or "No especificado",
            'Identificación': user.identification or "No disponible",
            'Contacto': user.contact or "No disponible",
            'Perfil Completo': "Completo" if user.is_profile_completed else "Incompleto",
            'Activo': "Sí" if user.is_active else "No",
            'Abogado GYM': "Sí" if user.is_gym_lawyer else "No",
            'Fecha de Registro': user.created_at.date()
        })

    # Create DataFrame and sort by registration date
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=['Fecha de Registro', 'Email'])

    # Build filter labels for metadata header
    role_label = ROLE_DISPLAY_MAP.get(filter_role, 'Todos') if filter_role else 'Todos'
    profile_label = {'complete': 'Completo', 'incomplete': 'Incompleto'}.get(filter_profile_status, 'Todos')
    doc_label = filter_document_type or 'Todos'
    period_start = start_date.strftime('%Y-%m-%d')
    period_end = end_datetime.strftime('%Y-%m-%d')

    METADATA_ROWS = 5

    # Create Excel file
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Usuarios Registrados', index=False, startrow=METADATA_ROWS)

        workbook = writer.book
        worksheet = writer.sheets['Usuarios Registrados']

        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'fg_color': '#1E3A5F',
            'font_color': '#FFFFFF',
            'border': 1,
            'valign': 'vcenter',
        })
        meta_format = workbook.add_format({
            'italic': True,
            'font_size': 10,
            'fg_color': '#F0F4F8',
            'border': 1,
        })
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D9D9D9',
            'border': 1
        })
        lawyer_format = workbook.add_format({'bg_color': '#E8F4FF'})
        client_format = workbook.add_format({'bg_color': '#F2F2F2'})
        corporate_format = workbook.add_format({'bg_color': '#E8FFE8'})
        basic_format = workbook.add_format({'bg_color': '#FFF8E8'})
        ROLE_ROW_FORMATS = {
            'Abogado': lawyer_format,
            'Cliente': client_format,
            'Cliente Corporativo': corporate_format,
            'Básico': basic_format,
        }
        _date_fmt = 'dd/mm/yyyy'
        ROLE_DATE_FORMATS = {
            'Abogado': workbook.add_format({'bg_color': '#E8F4FF', 'num_format': _date_fmt}),
            'Cliente': workbook.add_format({'bg_color': '#F2F2F2', 'num_format': _date_fmt}),
            'Cliente Corporativo': workbook.add_format({'bg_color': '#E8FFE8', 'num_format': _date_fmt}),
            'Básico': workbook.add_format({'bg_color': '#FFF8E8', 'num_format': _date_fmt}),
        }
        default_date_format = workbook.add_format({'bg_color': '#F2F2F2', 'num_format': _date_fmt})

        # Write metadata rows
        num_cols = len(df.columns) if not df.empty else 11
        worksheet.merge_range(0, 0, 0, num_cols - 1, 'Reporte de Usuarios Registrados', title_format)
        worksheet.write(1, 0, f'Generado el: {timezone.now().strftime("%Y-%m-%d %H:%M")}', meta_format)
        worksheet.write(2, 0, f'Período: {period_start} – {period_end}', meta_format)
        worksheet.write(3, 0, f'Filtro Rol: {role_label}', meta_format)
        worksheet.write(4, 0, f'Filtro Perfil: {profile_label}  |  Filtro Tipo Doc.: {doc_label}', meta_format)
        worksheet.set_row(0, 25)

        # Write column headers and set widths
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(METADATA_ROWS, col_num, value, header_format)
            if not df.empty:
                max_len = max(df[value].astype(str).map(len).max(), len(value)) + 2
                worksheet.set_column(col_num, col_num, max_len)

        # Apply row formatting by role
        if not df.empty:
            role_col_idx = df.columns.get_loc('Rol')
            date_col_idx = df.columns.get_loc('Fecha de Registro')
            for row_num, row in enumerate(df.values, start=METADATA_ROWS + 1):
                role = row[role_col_idx]
                row_format = ROLE_ROW_FORMATS.get(role, client_format)
                for col_num, value in enumerate(row):
                    if col_num == date_col_idx:
                        worksheet.write_datetime(
                            row_num, col_num, value,
                            ROLE_DATE_FORMATS.get(role, default_date_format)
                        )
                    else:
                        worksheet.write(row_num, col_num, value, row_format)

        # Add summary statistics
        if not df.empty:
            role_counts = df['Rol'].value_counts().reset_index()
            role_counts.columns = ['Rol', 'Cantidad']

            profile_counts = df['Perfil Completo'].value_counts().reset_index()
            profile_counts.columns = ['Estado', 'Cantidad']

            doc_counts = df['Tipo de Documento'].value_counts().reset_index()
            doc_counts.columns = ['Tipo de Documento', 'Cantidad']

            summary_row = METADATA_ROWS + len(df) + 3
            worksheet.write(summary_row, 0, 'Resumen por Rol de Usuario', header_format)
            summary_row += 1
            worksheet.write(summary_row, 0, 'Rol', header_format)
            worksheet.write(summary_row, 1, 'Cantidad', header_format)
            for _, row in role_counts.iterrows():
                summary_row += 1
                worksheet.write(summary_row, 0, row['Rol'])
                worksheet.write(summary_row, 1, row['Cantidad'])

            summary_row += 3
            worksheet.write(summary_row, 0, 'Resumen por Estado de Perfil', header_format)
            summary_row += 1
            worksheet.write(summary_row, 0, 'Estado', header_format)
            worksheet.write(summary_row, 1, 'Cantidad', header_format)
            for _, row in profile_counts.iterrows():
                summary_row += 1
                worksheet.write(summary_row, 0, row['Estado'])
                worksheet.write(summary_row, 1, row['Cantidad'])

            summary_row += 3
            worksheet.write(summary_row, 0, 'Resumen por Tipo de Documento', header_format)
            summary_row += 1
            worksheet.write(summary_row, 0, 'Tipo de Documento', header_format)
            worksheet.write(summary_row, 1, 'Cantidad', header_format)
            for _, row in doc_counts.iterrows():
                summary_row += 1
                worksheet.write(summary_row, 0, row['Tipo de Documento'])
                worksheet.write(summary_row, 1, row['Cantidad'])

    return response


def generate_user_activity_report(response, start_date, end_datetime):
    """
    Generate report of user activity with detailed information.

    Columns:
    - Usuario (User.email)
    - Nombre (User.first_name + User.last_name)
    - Tipo de Acción (ActivityFeed.action_type)
    - Descripción de Acción (ActivityFeed.description)
    - Fecha de Acción (ActivityFeed.created_at)
    """
    # Get activities created in the date range
    activities = ActivityFeed.objects.filter(
        created_at__range=[start_date, end_datetime]
    ).select_related('user')

    # Prepare data for Excel
    data = []

    for activity in activities:
        # Build user name
        user_name = f"{activity.user.first_name or ''} {activity.user.last_name or ''}".strip()

        # Get readable action type
        action_types = dict(ActivityFeed.ACTION_TYPE_CHOICES)
        action_type_display = action_types.get(activity.action_type, activity.action_type)

        # Add activity data to the list
        data.append({
            'Usuario': activity.user.email,
            'Nombre': user_name,
            'Tipo de Acción': action_type_display,
            'Descripción': activity.description,
            'Fecha de Acción': activity.created_at
        })

    # Create DataFrame and sort by timestamp (newest first)
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=['Fecha de Acción'], ascending=False)

        # Convertir fechas con zona horaria a fechas sin zona horaria
        if 'Fecha de Acción' in df.columns:
            df['Fecha de Acción'] = df['Fecha de Acción'].dt.tz_localize(None)

    # Create Excel file
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Actividad de Usuarios', index=False)

        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Actividad de Usuarios']

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D9D9D9',
            'border': 1
        })

        # Add action type formats for different actions
        create_format = workbook.add_format({'bg_color': '#E6F4EA'})  # Light green
        edit_format = workbook.add_format({'bg_color': '#E8F4FF'})    # Light blue
        delete_format = workbook.add_format({'bg_color': '#FCE8E6'})  # Light red
        other_format = workbook.add_format({'bg_color': '#F9F9F9'})   # Light gray

        # Write headers with format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            # Set column width based on max length in column
            if not df.empty:
                # Use a larger width for description column
                if value == 'Descripción':
                    worksheet.set_column(col_num, col_num, 50)
                else:
                    max_len = max(
                        df[value].astype(str).map(len).max(),
                        len(value)
                    ) + 2
                    worksheet.set_column(col_num, col_num, max_len)

        # Apply conditional formatting based on action type
        if not df.empty:
            # Get the index of the 'Tipo de Acción' column
            action_col_idx = df.columns.get_loc('Tipo de Acción')

            for row_num, row in enumerate(df.values, start=1):
                action_type = row[action_col_idx]

                # Select format based on action type
                if 'Create' in action_type or 'create' in action_type:
                    row_format = create_format
                elif 'Edit' in action_type or 'edit' in action_type or 'Update' in action_type or 'update' in action_type:
                    row_format = edit_format
                elif 'Delete' in action_type or 'delete' in action_type:
                    row_format = delete_format
                else:
                    row_format = other_format

                # Apply format to all cells in the row
                for col_num, value in enumerate(row):
                    worksheet.write(row_num, col_num, value, row_format)

        # Add summary statistics
        if not df.empty:
            # Count activities by action type
            if 'Tipo de Acción' in df.columns:
                action_counts = df['Tipo de Acción'].value_counts().reset_index()
                action_counts.columns = ['Tipo de Acción', 'Cantidad']

                # Count activities by user
                user_counts = df['Usuario'].value_counts().reset_index()
                user_counts.columns = ['Usuario', 'Cantidad de Acciones']

                # Write action type summary
                summary_row = len(df) + 3  # Leave 2 blank rows after main table
                worksheet.write(summary_row, 0, 'Resumen por Tipo de Acción', header_format)

                summary_row += 1
                worksheet.write(summary_row, 0, 'Tipo de Acción', header_format)
                worksheet.write(summary_row, 1, 'Cantidad', header_format)

                for idx, row in action_counts.iterrows():
                    summary_row += 1
                    worksheet.write(summary_row, 0, row['Tipo de Acción'])
                    worksheet.write(summary_row, 1, row['Cantidad'])

                # Write user activity summary
                summary_row += 3  # Add some space
                worksheet.write(summary_row, 0, 'Resumen por Usuario (Top 10)', header_format)

                summary_row += 1
                worksheet.write(summary_row, 0, 'Usuario', header_format)
                worksheet.write(summary_row, 1, 'Cantidad de Acciones', header_format)

                # Show only top 10 most active users
                for idx, row in user_counts.head(10).iterrows():
                    summary_row += 1
                    worksheet.write(summary_row, 0, row['Usuario'])
                    worksheet.write(summary_row, 1, row['Cantidad de Acciones'])

    return response


def generate_lawyers_workload_report(response, start_date, end_datetime):
    """
    Generate report of lawyers and their workload.

    Columns:
    - Abogado (User.email + User.first_name + User.last_name)
    - Total de Procesos Asignados (conteo)
    - Procesos Activos (conteo con filtro)
    - Procesos por Tipo de Caso (desglose)
    - Fecha de Registro (User.created_at)
    """
    # Filter lawyers - either a specific lawyer or all lawyers
    user_id = _get_user_id()
    if user_id:
        lawyers = User.objects.filter(id=user_id, role='lawyer')
    else:
        lawyers = User.objects.filter(role='lawyer')

    # Preserve the case catalogue's order without loading processes or stages.
    case_types = list(Case.objects.values_list('type', flat=True))
    fallo_stages = Process.stages.through.objects.filter(
        process_id=OuterRef('pk'), stage__status='Fallo',
    )
    workload_groups = (
        Process.objects.filter(
            lawyer_id__in=lawyers.values('pk'),
            created_at__range=[start_date, end_datetime],
        )
        .annotate(is_completed=Exists(fallo_stages))
        .values('lawyer_id', 'case__type', 'is_completed')
        .annotate(total=Count('pk'))
        .order_by()
    )
    workloads = {}
    for group in workload_groups.iterator(chunk_size=1000):
        counts = workloads.setdefault(group['lawyer_id'], {
            'total': 0, 'active': 0, 'completed': 0, 'cases': {},
        })
        counts['total'] += group['total']
        key = 'completed' if group['is_completed'] else 'active'
        counts[key] += group['total']
        case_type = group['case__type']
        counts['cases'][case_type] = counts['cases'].get(case_type, 0) + group['total']

    # Prepare data for Excel
    data = []

    for lawyer in lawyers:
        counts = workloads.get(lawyer.pk)
        if counts is None:
            continue
        total_processes = counts['total']
        active_processes = counts['active']
        completed_processes = counts['completed']
        case_type_counts = dict.fromkeys(case_types, 0)
        case_type_counts.update(counts['cases'])

        # Format case type distribution
        case_type_distribution = ', '.join([
            f"{case_type}: {count}" for case_type, count in case_type_counts.items() if count > 0
        ])

        # Format lawyer name and info
        lawyer_name = f"{lawyer.first_name or ''} {lawyer.last_name or ''}".strip()
        lawyer_email = lawyer.email

        # Add lawyer data to the list
        data.append({
            'Email': lawyer_email,
            'Nombre': lawyer_name,
            'Total de Procesos Asignados': total_processes,
            'Procesos Activos': active_processes,
            'Procesos Completados': completed_processes,
            'Distribución por Tipo de Caso': case_type_distribution,
            'Fecha de Registro': lawyer.created_at.date()
        })

    # Create DataFrame and sort by total processes (descending)
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=['Total de Procesos Asignados'], ascending=False)

    # Create Excel file
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Carga de Trabajo de Abogados', index=False)

        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Carga de Trabajo de Abogados']

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D9D9D9',
            'border': 1
        })

        # Write headers with format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            # Set column width based on max length in column
            if not df.empty:
                # Use a larger width for distribution column
                if value == 'Distribución por Tipo de Caso':
                    worksheet.set_column(col_num, col_num, 40)
                else:
                    max_len = max(
                        df[value].astype(str).map(len).max(),
                        len(value)
                    ) + 2
                    worksheet.set_column(col_num, col_num, max_len)

        # Add workload chart if there's data
        if not df.empty and len(df) > 1:  # Only create chart if there are multiple lawyers
            # Create a new worksheet for the chart
            chart_sheet = workbook.add_worksheet('Gráficos')

            # Write data for the chart
            chart_sheet.write(0, 0, 'Abogado', header_format)
            chart_sheet.write(0, 1, 'Procesos Activos', header_format)
            chart_sheet.write(0, 2, 'Procesos Completados', header_format)

            for i, row in df.iterrows():
                lawyer_name = row['Nombre'] or row['Email']
                chart_sheet.write(i+1, 0, lawyer_name)
                chart_sheet.write(i+1, 1, row['Procesos Activos'])
                chart_sheet.write(i+1, 2, row['Procesos Completados'])

            # Create a column chart
            chart = workbook.add_chart({'type': 'column'})

            # Add active and completed processes series
            chart.add_series({
                'name': 'Procesos Activos',
                'categories': ['Gráficos', 1, 0, len(df), 0],
                'values': ['Gráficos', 1, 1, len(df), 1],
                'fill': {'color': '#5B9BD5'}  # Blue for active processes
            })

            chart.add_series({
                'name': 'Procesos Completados',
                'categories': ['Gráficos', 1, 0, len(df), 0],
                'values': ['Gráficos', 1, 2, len(df), 2],
                'fill': {'color': '#70AD47'}  # Green for completed processes
            })

            # Configure chart
            chart.set_title({'name': 'Carga de Trabajo por Abogado'})
            chart.set_x_axis({'name': 'Abogado'})
            chart.set_y_axis({'name': 'Número de Procesos'})
            chart.set_style(10)

            # Insert chart
            chart_sheet.insert_chart('D2', chart, {'x_scale': 1.5, 'y_scale': 1.5})

            # Create a pie chart for total workload distribution
            pie_chart = workbook.add_chart({'type': 'pie'})

            # Prepare pie chart data
            chart_sheet.write(len(df)+3, 0, 'Abogado', header_format)
            chart_sheet.write(len(df)+3, 1, 'Total de Procesos', header_format)

            for i, row in df.iterrows():
                lawyer_name = row['Nombre'] or row['Email']
                chart_sheet.write(len(df)+4+i, 0, lawyer_name)
                chart_sheet.write(len(df)+4+i, 1, row['Total de Procesos Asignados'])

            # Add total processes series
            pie_chart.add_series({
                'name': 'Total de Procesos',
                'categories': ['Gráficos', len(df)+4, 0, len(df)*2+3, 0],
                'values': ['Gráficos', len(df)+4, 1, len(df)*2+3, 1],
                'data_labels': {'percentage': True, 'category': True}
            })

            # Configure pie chart
            pie_chart.set_title({'name': 'Distribución de Procesos entre Abogados'})
            pie_chart.set_style(10)

            # Insert pie chart
            chart_sheet.insert_chart('D20', pie_chart, {'x_scale': 1.5, 'y_scale': 1.5})

    return response
