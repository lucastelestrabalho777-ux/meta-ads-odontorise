#!/usr/bin/env python3
"""Testes offline do pdf.py (sem abrir navegador): nomes de arquivo, conferência de texto e modelos do pacote."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import pdf  # noqa: E402


class Nomes(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(pdf.slug("Ata reunião Dra. Ângela / novembro"), "ata-reuniao-dra-angela-novembro")
        self.assertEqual(pdf.slug("   "), "documento")

    def test_nome_pdf(self):
        self.assertEqual(pdf.nome_pdf("Leitura dos grupos 06 a 12"), "Leitura_dos_grupos_06_a_12_OdontoRise.pdf")


class Conferencia(unittest.TestCase):
    def test_limpo(self):
        self.assertEqual(pdf.conferir_texto("<body><p>Reunião em 13/11 com 3 pessoas, às 10:00.</p></body>"), [])

    def test_travessao(self):
        self.assertTrue(any("travessão" in a for a in pdf.conferir_texto("<p>Resultado \u2014 bom</p>")))

    def test_travessao_no_estilo_nao_conta(self):
        self.assertEqual(pdf.conferir_texto("<style>/* a \u2014 b */</style><!-- x \u2014 y --><p>ok</p>"), [])

    def test_sobra_do_modelo(self):
        avisos = pdf.conferir_texto("<h1>Título do documento</h1><div>00</div>")
        self.assertEqual(len(avisos), 2)

    def test_numero_real_nao_e_sobra(self):
        self.assertEqual(pdf.conferir_texto("<p>100 leads, 2.00 de custo, sala 300</p>"), [])


class Modelos(unittest.TestCase):
    def test_modelos_existem_e_avisam(self):
        for nome, marca in (("documento.html", 'class="page'), ("apresentacao.html", 'class="slide')):
            caminho = os.path.join(pdf.MODELOS, nome)
            self.assertTrue(os.path.isfile(caminho), nome)
            html = open(caminho, encoding="utf-8").read()
            self.assertIn(marca, html)
            self.assertNotIn("\u2014", html)
            # o modelo cru precisa ser barrado pela conferência
            self.assertTrue(any("sobrou texto do modelo" in a for a in pdf.conferir_texto(html)), nome)
        self.assertTrue(os.path.isfile(os.path.join(pdf.MODELOS, "logo.png")))


if __name__ == "__main__":
    unittest.main()
