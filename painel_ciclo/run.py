# -*- coding: utf-8 -*-
"""
Ponto de entrada do bloco coincidente.

Uso:
    python -m painel_ciclo.run            # roda com a data de hoje
    python -m painel_ciclo.run --offline  # usa cache se a fonte falhar

Identifica o fechamento vigente no calendário 2026, coleta os dados reais,
calcula as três métricas, classifica a cor do bloco coincidente e grava
as saídas em painel_ciclo/saidas/.
"""
import sys
import datetime as dt

from . import config
from . import coincidente


def fechamento_vigente(hoje=None):
    """Retorna a entrada do calendário cuja data de fechamento é a próxima >= hoje."""
    hoje = hoje or dt.date.today()
    futuros = [c for c in config.CALENDARIO_2026
               if dt.date.fromisoformat(c["fechamento"]) >= hoje]
    if futuros:
        return futuros[0]
    return config.CALENDARIO_2026[-1]


def main(argv=None):
    argv = argv or sys.argv[1:]
    usar_cache = "--offline" in argv

    # garante UTF-8 no console (Windows usa cp1252 por padrão)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    hoje = dt.date.today()
    fech = fechamento_vigente(hoje)
    print(f"Data de hoje: {hoje.isoformat()}")
    print(f"Fechamento vigente: {fech['fechamento']}  | mês de referência alvo: {fech['referencia']}")
    print("Observação: cada série usa o ÚLTIMO MÊS FECHADO disponível na fonte.\n")
    print("Coletando séries oficiais (BCB/SGS e IBGE/SIDRA)...")

    df, diag, log, _, _ = coincidente.constroi(usar_cache=usar_cache)

    print("\n--- Status da coleta ---")
    for k, v in log.items():
        print(f"  {k:16s} {v}")

    print("\n--- Métricas por indicador ---")
    print(df.to_string(index=False))

    print("\n--- Diagnóstico do bloco coincidente ---")
    print(f"  COR: {diag['cor']}   |   Ct = {diag['ct']}")
    if diag["n_nucleo"]:
        print(f"  Núcleo: {diag['n_nucleo']} indicadores  "
              f"(crescendo {diag['n_pos']} / caindo {diag['n_neg']})")
        print(f"  Difusão positiva: {diag['share_pos']*100:.0f}%  | "
              f"intensidade das quedas: {diag['intensidade']:.2f}%")

    csv_path, md_path, _ = coincidente.grava_saidas(df, diag, log,
                                                    data_ref=fech["fechamento"])
    print(f"\nSaídas gravadas:\n  {csv_path}\n  {md_path}")


if __name__ == "__main__":
    main()
