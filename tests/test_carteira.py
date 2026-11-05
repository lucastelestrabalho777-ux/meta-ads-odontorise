"""Classificação da carteira por gestor (scripts/carteira.py), offline, sem token e sem rede.

Casos tirados da leitura real de 03/11/2026 (números reais, sem dado pessoal):
Tamires (melhor, mas 25 dias parada), Maria Luiza (bom, saldo zerado), Emanuel (recente, custo R$223,95),
Julia (recente, ONB1, sem cadastro), Thalita (UNSETTLED), Sandriny (#200 sem leitura), ZM (ficha crítica, 0 campanhas ativas).
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import carteira  # noqa: E402

HOJE = date(2026, 11, 3)


def resultado(msgs, custo, gasto, saldo=None, recencia=None, campanhas_ativas=1, status_conta="ATIVA", pendente=0.0, ads_sem_msg=0):
    saldo_sinal = {"status": "ok", "status_conta": status_conta, "valor_pendente_cobranca": pendente}
    if status_conta != "ATIVA":
        saldo_sinal["status"] = "critico"
    if saldo is not None:
        saldo_sinal.update({"pre_paga": True, "saldo_restante": saldo, "status": "critico" if saldo <= 0 else "ok"})
    rec = {"status": "ok", "dias_sem_alteracao": recencia or 1}
    if recencia and recencia >= 11:
        rec["status"] = "critico"
    elif recencia and recencia >= 7:
        rec["status"] = "atencao"
    gasto_sinal = {"status": "critico" if custo and custo >= 35 else "ok",
                   "conta_7d": {"gasto": gasto, "mensagens": msgs, "custo_por_mensagem": custo},
                   "conta_7d_anteriores": {"gasto": 0, "mensagens": 0, "custo_por_mensagem": None},
                   "campanhas_ativas": campanhas_ativas, "custo_acima_do_teto": bool(custo and custo >= 35),
                   "campanhas_sem_resultado": [], "campanhas": []}
    criativos = {"status": "critico" if ads_sem_msg else "ok", "sem_resultado": ads_sem_msg,
                 "anuncios_sem_resultado": [{"gasto_7d": 87.79}] * ads_sem_msg}
    return {"ok": True, "cliente": "x", "conta": {"act_id": "act_1", "nome": "CA"},
            "janelas": {"atual": {"desde": "2026-10-27", "ate": "2026-11-02"}},
            "resumo": {"status": "ok", "critico": [], "atencao": [], "erro": []},
            "sinais": {"saldo_pagamento": saldo_sinal, "anuncios_problema": {"status": "ok"}, "gasto_sem_resultado": gasto_sinal,
                       "criativos_sem_resultado": criativos, "recencia": rec}}


def ficha(**k):
    base = {"cadastrado": True, "act_id": "act_1", "status": "ativo", "gestor": ["Naoki Kanda"]}
    base.update(k)
    return base


class Classificacao(unittest.TestCase):
    def test_melhor_mesmo_parada(self):
        l = carteira.classificar(ficha(nome="DRA TAMIRES MARQUES", codigo="#401", produto="Select", satisfacao="Satisfeito",
                                       data_fechamento="2026-07-23"), resultado(33, 14.06, 464, recencia=25), HOJE)
        self.assertEqual(l["classe"], "melhor")
        self.assertIn("⭐", l["marcadores"])
        self.assertIn("🔴", l["marcadores"])
        self.assertIn("25d parada", l["situacao"])
        self.assertFalse(l["recente"])

    def test_bom_com_saldo_zerado(self):
        l = carteira.classificar(ficha(nome="DRA MARIA LUIZA FLORÊNCIO", codigo="#395", ticket=2297.0, satisfacao="Satisfeito",
                                       data_fechamento="2026-07-13"), resultado(18, 21.18, 381, saldo=0, recencia=21), HOJE)
        self.assertEqual(l["classe"], "bom")
        self.assertIn("saldo R$0 (parada)", l["situacao"])
        self.assertEqual(carteira._col_7d(l), "18 · R$21,18")

    def test_recente_com_custo_acima_do_teto(self):
        l = carteira.classificar(ficha(nome="DR EMANUEL ARAÚJO", codigo="#438", satisfacao="Neutro", data_fechamento="2026-10-16",
                                       gestor=["Christopher Mcnelson"]), resultado(1, 223.95, 223.95, ads_sem_msg=2), HOJE)
        self.assertTrue(l["recente"])
        self.assertEqual(l["classe"], "ruim")
        self.assertIn("custo R$223,95", l["situacao"])
        self.assertIn("2 anúncio(s) R$175,58 sem msg", l["situacao"])

    def test_sem_cadastro_em_onboarding(self):
        l = carteira.classificar({"nome": "DRA JULIA OLIVEIRA", "codigo": "#445", "status": "ativo", "fase": "ONB1", "produto": "Start",
                                  "ticket": 2750.0, "data_fechamento": "2026-10-28", "gestor": ["Christopher Mcnelson"], "cadastrado": False},
                                 None, HOJE)
        self.assertEqual(l["leitura"], "sem_cadastro")
        self.assertTrue(l["recente"])
        self.assertIn("ONB1", l["situacao"])
        self.assertIn("sem cadastro local", l["situacao"])
        self.assertEqual(carteira._col_7d(l), "sem conta")

    def test_conta_unsettled(self):
        l = carteira.classificar(ficha(nome="DRA THALITA BUENO (CA antiga PROMOVADS)", codigo="#429", satisfacao="Neutro",
                                       data_fechamento="2026-10-02"), resultado(6, 56.94, 341, status_conta="UNSETTLED", pendente=812.84), HOJE)
        self.assertIn("conta UNSETTLED (R$812,84 pendente)", l["situacao"])
        self.assertEqual(l["nome_curto"], "Thalita Bueno")

    def test_sem_leitura(self):
        l = carteira.classificar(ficha(nome="DRA. ANDREA SANDRINY", codigo="#362", satisfacao="Neutro", data_fechamento="2026-04-29"),
                                 {"ok": False, "act_id": "act_1", "cliente": "x", "erro": "(#200) sem permissão", "code": 200}, HOJE)
        self.assertEqual(l["leitura"], "erro")
        self.assertIn("⚠️", l["marcadores"])
        self.assertEqual(carteira._col_7d(l), "sem leitura (#200)")

    def test_ficha_critica_nao_vira_melhor_e_zero_campanhas_e_critico(self):
        l = carteira.classificar(ficha(nome="ZM ODONTOLOGIA AVANÇADA", codigo="#411", produto="Select", satisfacao="Muito Insatisfeito (Crítico)",
                                       data_fechamento="2026-08-21"), resultado(26, 15.16, 394, campanhas_ativas=0), HOJE)
        self.assertEqual(l["classe"], "bom")
        self.assertIn("0 campanhas ativas", l["situacao"])
        alertas = carteira.alertas_relacionamento([l])
        self.assertEqual(alertas[0]["tipo"], "ficha_critica_conta_mal")


class Texto(unittest.TestCase):
    def test_nome_curto(self):
        self.assertEqual(carteira.nome_curto("DRA. PATRÍCIA ROCHA"), "Patrícia Rocha")
        self.assertEqual(carteira.nome_curto("CONNECTODONTO JAGUARIAÍVA"), "Connectodonto Jaguariaíva")
        self.assertEqual(carteira.nome_curto("Clínica Selectta Odontologia"), "Clínica Selectta Odontologia")
        self.assertEqual(carteira.nome_curto("ZM ODONTOLOGIA AVANÇADA."), "ZM Odontologia Avançada")
        self.assertEqual(carteira.nome_curto("DR ERY DHEIGLY"), "Ery Dheigly")

    def test_erro_curto_e_dias(self):
        self.assertEqual(carteira.erro_curto("(#200) Ad account owner has NOT grant ads_read permission, refer to https://x", 200),
                         "#200: conta fora da BM ou sem ads_read")
        self.assertEqual(carteira._dias(0.7), "0,7d")
        self.assertEqual(carteira._dias(11.0), "11d")

    def test_satisfacao_curta(self):
        self.assertEqual(carteira.satisfacao_curta("Muito Insatisfeito (Crítico)"), "Crítico")
        self.assertEqual(carteira.satisfacao_curta("Muito Satisfeito (Promotor)"), "Promotor")
        self.assertEqual(carteira.satisfacao_curta("Insatisfeito (Alerta)"), "Alerta")
        self.assertEqual(carteira.satisfacao_curta(None), "sem")

    def test_data_de_entrada_prefere_fechamento(self):
        self.assertEqual(carteira.data_entrada({"data_fechamento": "2026-10-20", "data_1o_pagamento": "2026-10-15", "criado": "2026-10-01"}),
                         ("2026-10-20", "data_fechamento"))
        self.assertEqual(carteira.data_entrada({"criado": "2026-10-01"}), ("2026-10-01", "criado"))

    def test_tabela_sem_travessao(self):
        linhas = [carteira.classificar(ficha(nome="DRA TAMIRES MARQUES", codigo="#401", produto="Select", satisfacao="Satisfeito",
                                             data_fechamento="2026-07-23"), resultado(33, 14.06, 464), HOJE)]
        t = carteira.tabela_gestor("Naoki", linhas, HOJE)
        self.assertIn("| 401 | Tamires Marques | Select (sem ticket) | 23/07 | Satisfeito | 33 · R$14,06 | ⭐ |", t)
        self.assertIn("⭐ **Melhores**: Tamires Marques (33 · R$14,06, Satisfeito)", t)
        self.assertNotIn("\u2014", t)


if __name__ == "__main__":
    unittest.main()
