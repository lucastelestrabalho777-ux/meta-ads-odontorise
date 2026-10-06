# Regras da casa (OdontoRise)

Valem em toda operação, em qualquer conta, para qualquer papel. Não são sugestões.

1. **Nada executado sem OK explícito, item por item.** O Claude analisa, apresenta sugestões numeradas
   e só faz o que o gestor aprovar. OK em um item não vale para os outros. OK em uma conta não vale para outra.
2. **Tudo nasce pausado.** Campanha, conjunto e anúncio são criados com status PAUSED. Ativar é decisão
   do gestor, depois de conferir preview e auditoria do conjunto.
3. **Antes de pausar, cruzar 30, 14 e 7 dias por anúncio.** Um anúncio só sai quando está ruim nas três
   janelas. Nunca decidir por uma janela só.
4. **Nunca ampliar raio de localização.** Escala vem de criativo, verba e público. Posicionamento (Instagram,
   Facebook) segue o que a conta do cliente já usa: não incluir nem tirar plataforma sem entender o que está rodando.
5. **Post do Instagram do cliente passa por análise antes de virar anúncio.** O Claude lê o conteúdo e
   classifica: fala com o paciente final, sobe; mentoria, conteúdo pessoal ou sem sentido para captação,
   não sobe e o gestor é avisado.
6. **Rosto de paciente só com termo de consentimento assinado.** Foto de consultório: conferir se não há
   tela com dados de paciente.
7. **Campanha sem resultado exige ação**, nunca "observar": propor criativo, público, verba ou pausa.
8. **Orçamento em centavos na API.** Confirmar o valor em reais com o gestor antes de enviar.
9. **Resultado de conta se quebra por campanha** antes de atribuir gasto ou mensagens a uma campanha.
10. **Métricas da casa:** mensagens iniciadas, custo por mensagem iniciada, gasto, CTR, CPM, alcance,
    impressões, frequência. Não usamos custo por lead de formulário ou site.
11. **Segredo nunca aparece**: token, chave secreta e senha não entram em resposta, nota, memória ou print.
12. **Textos sem travessão.** Dois-pontos, vírgula ou ponto.
13. **Cliente com mais de uma conta de anúncio:** informar qual tem pagamento válido antes de subir qualquer coisa.
14. **Cada pessoa só lê e opera as contas dos clientes que cuida.** A lista é o cadastro local, montado a partir do
    campo Gestor do ClickUp (`clientes.py meus`). Conta fora do cadastro: os scripts recusam e o Claude não contorna
    (não chama `--account` de outro cliente, não cadastra cliente de outro gestor, não lista resultado de conta alheia).
    Só o head cadastra a carteira inteira, gestor por gestor (`meus --gestor NOME` e `cadastrar --carteira`).
15. **Limiares da saúde da conta:** custo por mensagem de R$35 ou mais é crítico; anúncio ativo com R$50 (atenção) ou
    R$100 (crítico) gastos em 7 dias sem mensagem; campanha com R$150 sem mensagem é crítico; conta sem alteração humana
    há 7 dias é atenção e há mais de 10 dias é crítico.
