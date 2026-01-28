def es_fila_valida(row):
    """
    Valida si una fila de CSV conté les dades necessàries per definir un bloc.
    Requereix: dx, dy, dz (enters) i material (string no "").
    """
    required_keys = ['dx', 'dy', 'dz', 'material']
    if not all(key in row for key in required_keys):
        return False

    try:
        int(row['dx'])
        int(row['dy'])
        int(row['dz'])
    except ValueError:
        return False

    if not row['material'] or not isinstance(row['material'], str):
        return False

    return True
