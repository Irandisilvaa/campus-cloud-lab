# Roteiro para gravar o tutorial prático

**Formato:** vídeo de apoio de aproximadamente 20–25 minutos, com pausas sugeridas para execução. Não é um vídeo pronto nem link de YouTube. A aula completa continua com 90 minutos. Grave usando um domínio real autorizado e uma conta de laboratório ensaiada. Corte esperas, informando quanto tempo realmente passou.

| Trecho | Tela e ação | Fala sugerida |
|---|---|---|
| 0:00–1:30 | Portal final e diagrama do README | “Vamos publicar esse portal usando sete serviços. O código já está pronto; o trabalho da aula é entender e configurar a infraestrutura.” |
| 1:30–3:00 | Repositório, README e pasta infra | “Na primeira vez usamos clone. Pull atualiza a cópia existente. Os templates já incluem a aplicação.” |
| 3:00–5:00 | Academy e upload de 01-base | “Confiram a região, a AMI indicada pelo professor e duas zonas diferentes. O template cria a rede e dois servidores privados.” |
| 5:00–7:00 | VPC, subnets, rotas e IGW | “A rota ao Internet Gateway caracteriza a subnet pública. Os servidores estão nas privadas e não possuem IP público.” |
| 7:00–9:00 | SGs e listener/target group | “A porta 8080 aceita somente a origem do SG do ALB. O listener recebe a requisição, e o target group define para onde encaminhá-la.” |
| 9:00–11:00 | Portal, parar EC2 A, targets e recuperar | “Vamos interromper um servidor. A detecção leva tempo; após isso, o outro continua atendendo. O ALB não cria uma nova EC2.” |
| 11:00–13:00 | Stack DNS privado e botão de consulta | “Esta consulta parte da EC2. Por isso consegue resolver o nome privado que o notebook, fora da VPC, não resolve.” |
| 13:00–16:00 | Delegação NS, zona pública e CNAME ACM já preparados | “Esses recursos foram preparados antes da aula. Precisamos controlar o domínio público. Uma zona privada não resolve a validação do ACM.” |
| 16:00–18:00 | 05-https, listener 443, A Alias e certificado | “Agora conectamos o nome público ao ALB e associamos o certificado ao listener. TLS termina no ALB.” |
| 18:00–19:00 | Atualizar HttpsHost na base | “Só ativamos o redirecionamento depois de verificar HTTPS funcionando.” |
| 19:00–22:00 | 06-waf Count e depois Block | “Count observa a regra sem bloquear. Block impede o caminho /admin. Isso demonstra inspeção de aplicação, diferente do filtro de portas do SG.” |
| 22:00–25:00 | Evidências e exclusão na ordem do tutorial | “A limpeza faz parte do laboratório. Encerrar a sessão não é o mesmo que excluir ALB, zonas e WAF.” |

Na descrição do vídeo, inclua o link real do repositório e o tutorial do aluno. Não afirme que o lab funciona em qualquer modalidade do Academy. Não mostre tokens, credenciais temporárias ou abas com informações pessoais. Mostre erros reais relevantes e sua correção; não rotule gravação editada como implantação instantânea.
