import os
from utils.functional import (
    load_logs,
    count_logs_by_level,
    get_agent_activity,
    filter_logs,
)


def main():
    # Definir path al fitxer de log
    log_file = os.path.join(os.path.dirname(__file__), "minecraft_agents.log")

    print(f"ANÀLISI DE LOGS FUNCIONAL: {log_file}")
    print("=" * 60)

    if not os.path.exists(log_file):
        print("ERROR: El fitxer de log no existeix.")
        return

    # REDUCE - Comptar logs per level (INFO, DEBUG, WARNING I ERROR)
    # recreem el generador per a cada anàlisi (lazy).

    print("\n--- Distribució per level (REDUCE) ---")
    logs_gen = load_logs(log_file)
    level_counts = count_logs_by_level(logs_gen)
    for level, count in level_counts.items():
        print(f"{level}: {count}")

    # REDUCE - compta logs per agent
    print("\n--- nLogs per Agent (REDUCE) ---")
    logs_gen = load_logs(log_file)
    activity = get_agent_activity(logs_gen)
    sorted_activity = sorted(activity.items(), key=lambda x: x[1], reverse=True)
    for agent, count in sorted_activity:
        print(f"{agent}: {count}")

    # FILTER - filtra errors i els mostra
    print("\n--- Ultims 5 Errors (FILTER) ---")
    logs_gen = load_logs(log_file)
    errors = filter_logs(logs_gen, level="ERROR")

    # Convertim a llista només els errors per poder mostrar els últims
    error_list = list(errors)
    last_errors = error_list[-5:] if error_list else []

    if not last_errors:
        print("Cap error trobat.")
    else:
        for i, err in enumerate(last_errors, 1):
            print(
                f"{i}. [{err.get('timestamp')}] {err.get('logger')}: {err.get('message')}"
            )

    print("\n" + "=" * 60)
    print("Anàlisi complet")


if __name__ == "__main__":
    main()
