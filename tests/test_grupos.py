#!/usr/bin/env python3
"""Testes offline do grupos.py (sem rede): horário útil, mensagem que só encerra, filtro de atrito, trava de rota."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import grupos  # noqa: E402
from lib import uazapi  # noqa: E402


class HorarioUtil(unittest.TestCase):
    def test_mesmo_dia(self):
        self.assertEqual(grupos.minutos_uteis(datetime(2026, 11, 11, 10, 0), datetime(2026, 11, 11, 10, 45)), 45)

    def test_noite_nao_conta(self):
        # quarta 17h30 até quinta 8h20 = 30 min de quarta + 20 min de quinta
        self.assertEqual(grupos.minutos_uteis(datetime(2026, 11, 11, 17, 30), datetime(2026, 11, 12, 8, 20)), 50)

    def test_fim_de_semana_nao_conta(self):
        # sexta 17h até segunda 9h = 60 + 60
        self.assertEqual(grupos.minutos_uteis(datetime(2026, 11, 13, 17, 0), datetime(2026, 11, 16, 9, 0)), 120)

    def test_mensagem_de_madrugada(self):
        self.assertEqual(grupos.minutos_uteis(datetime(2026, 11, 11, 23, 0), datetime(2026, 11, 12, 8, 30)), 30)


class Encerramento(unittest.TestCase):
    def _m(self, texto, tipo="Conversation"):
        return {"text": texto, "messageType": tipo}

    def test_encerra(self):
        for t in ("Ok", "Beleza", "Muito obrigada!", "Perfeito, obrigado", "kkkk", "Bom dia", "Tá bom"):
            self.assertTrue(grupos._so_encerra(self._m(t)), t)

    def test_nao_encerra(self):
        for t in ("Deu certo?", "Ok, mas e o estorno?", "Bom dia, não está chegando lead", "50"):
            self.assertFalse(grupos._so_encerra(self._m(t)), t)

    def test_audio_nao_encerra(self):
        self.assertFalse(grupos._so_encerra(self._m("", "AudioMessage")))


class Atrito(unittest.TestCase):
    def test_pega(self):
        for t in ("Acho q não vale o investimento", "Não está chegando o leed", "podemos pausar",
                  "Ainda não caiu nenhum lead", "quero cancelar o contrato"):
            self.assertTrue(grupos.RE_ATRITO.search(t), t)

    def test_nao_pega(self):
        for t in ("Bom dia, segue o resultado da semana", "Obrigada pelo retorno rápido"):
            self.assertFalse(grupos.RE_ATRITO.search(t), t)


class SoLeitura(unittest.TestCase):
    def test_rotas(self):
        self.assertEqual(set(uazapi.ROTAS_LEITURA), {"/instance/status", "/group/list", "/message/find", "/message/download"})

    def test_recusa_envio(self):
        for rota in ("/send/text", "/message/markread", "/group/leave", "/webhook", "/message/delete"):
            with self.assertRaises(uazapi.ErroUazapi):
                uazapi.chamar(rota, {})


if __name__ == "__main__":
    unittest.main()
