# Evidências de laboratório — Campus na Nuvem (sem domínio)

**Grupo:** __________  **Integrantes:** __________  **Data:** __________  **Região:** __________  **Prefixo das stacks:** __________

**Preenchimento:** use `APROVADO`, `FALHOU` ou `NÃO EXECUTADO` e descreva o que ocorreu. Capturas não devem conter credenciais, tokens, chaves ou dados pessoais. IDs de instâncias/contas são específicos da execução; não devem ser reutilizados por outro grupo.

| Item | O que precisa ser comprovado | Situação | Captura / observação |
|---|---|---|---|
| CloudFormation | Stack base `CREATE_COMPLETE` | | |
| Aplicação | `/health`: `ok`, `/api/eventos`: 3 eventos | | |
| ALB | Dois targets `healthy`, respostas A e B | | |
| VPC | Quatro subnets, dois AZs, CIDRs previstos | | |
| Rotas | Pública ao IGW, privadas sem rota padrão | | |
| Security Groups | ALB 80; EC2 só 8080 do ALB; SSH não aberto | | |
| EC2 | Duas `running` sem IPv4 público | | |
| Falha | Parar uma instância, observar outra atender; registrar falhas transitórias | | |
| Recuperação | Ambas voltam a `healthy` | | |
| DNS privado | `app.campus.internal` resolve IPs privados da própria stack | | |
| WAF Count | `/admin` retorna HTTP 200 | | |
| WAF Block | `/admin` 403, `/` 200 após propagação | | |
| DNS público | Somente se domínio delegado e autorizado | NÃO EXECUTADO, se sem domínio | |
| ACM e HTTPS | Somente com certificado ISSUED e domínio próprio | NÃO EXECUTADO, se sem domínio | |
| Limpeza | WAF, DNS privado e base excluídos; recursos do grupo removidos | | |

## Respostas conceituais

1. **Como EC2 sem IP público consegue responder ao navegador pela internet?**

   Resposta: ______________________________________________

2. **O que faz uma subnet ser pública? Qual a função da rota `0.0.0.0/0` e do Internet Gateway?**

   Resposta: ______________________________________________

3. **Qual a diferença entre Security Group e regra de URI do WAF?**

   Resposta: ______________________________________________

4. **Por que ocorreu (ou poderia ocorrer) erro 504 na parada de uma EC2? O ALB cria uma instância substituta?**

   Resposta: ______________________________________________

5. **Por que o DNS privado não habilita HTTPS público? Onde ocorreria o término TLS se o certificado estivesse configurado?**

   Resposta: ______________________________________________

6. **Quais ações CloudFormation automatizou e quais dependem das permissões do Learner Lab?**

   Resposta: ______________________________________________

## Limitações e encerramento

**Serviços indisponíveis ou não executados, com motivo:** ______________________________________________

**Falhas encontradas e soluções/limites:** ______________________________________________

**Horário de início e término:** ______________________________________________

**Confirmação de exclusão das stacks e recursos do grupo:** ______________________________________________

> Nunca marque como aprovado um recurso previsto nos templates mas não executado. Sem domínio público controlado, DNS público/ACM/HTTPS permanecem **NÃO EXECUTADOS**.
