# Evidências do grupo

Grupo: ______  Integrantes: ______  Região: ______  Data: ______

Não inclua credenciais, tokens ou chaves nas capturas. Use somente dados fictícios.

| Item | Evidência esperada | Resultado/arquivo |
|---|---|---|
| CloudFormation | Base CREATE_COMPLETE e lista de recursos | |
| VPC | /16, quatro /24, rota pública ao IGW e privadas sem rota de internet | |
| SG | 8080 aceita apenas SG do ALB; ausência de SSH | |
| ALB | Dois targets healthy e portal funcionando | |
| Falha | Uma EC2 parada; outra continua atendendo depois da detecção | |
| Recuperação | Dois targets healthy novamente | |
| DNS privado | Resolução de app.campus.internal pelo servidor | |
| DNS público | Zona delegada e A Alias para ALB | |
| ACM | ISSUED e certificado válido no hostname do navegador | |
| HTTPS | HTTP redireciona para HTTPS no hostname correto | |
| WAF | /admin 200 em Count e 403 em Block; / continua 200 | |
| Limpeza | Stacks excluídas e nenhum recurso do grupo restante | |

1. Por que as EC2 privadas conseguem responder a usuários públicos através do ALB?

Resposta: ______

2. O que torna uma subnet pública? Qual o papel do IGW e da route table?

Resposta: ______

3. Como stateful explica as respostas das EC2 mesmo sem uma saída geral liberada?

Resposta: ______

4. Por que private hosted zone não permite validar o certificado público deste portal?

Resposta: ______

5. Qual a diferença entre uma restrição do SG e uma regra de URI no WAF?

Resposta: ______

6. Onde termina TLS? O ALB cria novas EC2 automaticamente?

Resposta: ______

7. Que serviço faltou executar por restrição do ambiente, se houve? Não marque como concluído algo apenas explicado.

Resposta: ______
