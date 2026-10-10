# SPORT 5 AI — correção do radar de notícias

## O que foi corrigido
- Porta local padronizada em `8000`, igual aos scripts de inicialização.
- Leitura RSS/Atom com suporte a links Atom (`href`) e datas de publicação.
- Filtro de notícias publicadas nas últimas 48 horas; itens sem data válida não entram no radar ativo.
- Deduplicação por URL e título.
- Não altera a data de notícias antigas quando não há novidades.
- Registros legados sem timestamp original são arquivados e deixam de aparecer como notícias recentes verificadas.
- Notícia capturada por um único RSS fica `IN_VERIFICATION`, com confiança conservadora e produção bloqueada até checagem.
- Endpoint `/api/status` informa tentativa/sucesso/erro da última sincronização e estado dos feeds.
- Atualização do navegador sem cache e sincronização manual com mensagem honesta em caso de falha.

## Executar no Windows
1. Extraia todos os arquivos para uma única pasta.
2. Abra `iniciar_sport5.bat`.
3. O navegador abre `http://localhost:8000`.
4. Para conferir a saúde do backend, abra `http://localhost:8000/api/status`.
5. Para conferir as pautas: `http://localhost:8000/api/pautas`.

## Executar no macOS/Linux
Execute `chmod +x iniciar_sport5.sh` uma vez e depois `./iniciar_sport5.sh`.

## Publicar no Render
1. Substitua os arquivos do repositório pelos arquivos corrigidos desta pasta.
2. Faça commit e push para o GitHub.
3. No Render, execute um novo deploy.
4. Abra `https://SEU-SERVICO.onrender.com/api/status` e confira `last_sync_attempt`, `last_sync_success`, `last_sync_error` e `feeds`.
5. Abra o aplicativo e clique em **Sincronizar Feeds ao Vivo** para testar.

O Render fornece a variável `PORT` automaticamente. O servidor usa essa variável em produção e usa a porta `8000` por padrão no computador local.

## Limites importantes
- A aplicação busca manchetes por RSS. Encontrar uma manchete no RSS **não significa que o fato foi confirmado**. A pauta permanece pendente até ser checada em matéria original e, idealmente, fonte oficial ou segunda fonte independente.
- O código não usa uma API de notícias paga nem chama Gemini/OpenAI para checagem factual.
- Instâncias gratuitas de hospedagem podem suspender serviços inativos e o armazenamento local pode ser efêmero. Para monitoramento contínuo e histórico persistente, use uma instância que permaneça ativa e um banco persistente.
- Se os feeds falharem, o status mostrará a falha; o sistema não atualizará datas antigas nem fingirá que houve notícias novas.
