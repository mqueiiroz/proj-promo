<?php if ($falhaLocal !== null): ?>
    <p class="mensagem monitoramento" role="status">Última falha de infraestrutura registrada em <?= escaparMonitoramento($falhaLocal) ?>. Consulte o log local da coleta para acompanhar o ocorrido.</p>
<?php endif; ?>
<?php if ($monitoramento === null): ?>
    <p class="mensagem monitoramento" role="alert">Não foi possível consultar o monitoramento agora. Tente novamente mais tarde.</p>
<?php else: ?>
    <?php foreach ($monitoramento['lojas'] as $loja): ?>
        <?php if ($loja['TIPO'] === 'COLETA_FALHA'): ?>
            <p class="mensagem monitoramento aviso-coleta" role="status"><strong>Falha na coleta de <?= escaparMonitoramento($loja['NOME']) ?>.</strong> Os dados anteriores foram preservados nas operações que falharam.</p>
        <?php endif; ?>
    <?php endforeach; ?>
    <section class="monitoramento" aria-labelledby="ofertas-monitoradas">
        <h2 class="sr-only" id="ofertas-monitoradas">Ofertas monitoradas</h2>
        <?php if ($monitoramento['ofertas'] === []): ?>
            <p>Nenhuma oferta monitorada.</p>
        <?php else: ?>
            <div class="tabela-eventos tabela-gestao" tabindex="0" role="region" aria-labelledby="ofertas-monitoradas">
                <table aria-labelledby="ofertas-monitoradas">
                    <thead><tr>
                        <th scope="col">Produto</th><th scope="col">Loja</th><th scope="col">Fonte</th>
                        <th scope="col">Cadastrado em</th><th scope="col">Promoção desde</th>
                        <th scope="col">Última coleta</th><th scope="col">Status</th><th scope="col">Ação</th>
                    </tr></thead>
                    <tbody>
                        <?php foreach ($monitoramento['ofertas'] as $oferta): ?>
                            <tr>
                                <td><?= escaparMonitoramento($oferta['NOME']) ?></td>
                                <td><?= escaparMonitoramento($oferta['LOJA']) ?></td>
                                <td>Coleta local</td>
                                <td><?= escaparMonitoramento($oferta['CADASTRADO_EM'] ?? '—') ?></td>
                                <td><?= escaparMonitoramento($oferta['PROMOCAO_DESDE'] ?? '—') ?></td>
                                <td><?= escaparMonitoramento($oferta['ULTIMA_COLETA'] ?? '—') ?></td>
                                <td><?= escaparMonitoramento($oferta['STATUS']) ?></td>
                                <td><a class="acao-secundaria" href="/produto.html?id=<?= rawurlencode((string) $oferta['ID']) ?>">Ver detalhes</a></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </section>
    <section class="monitoramento" aria-labelledby="status-lojas">
        <h2 id="status-lojas">Status por loja</h2>
        <?php if ($monitoramento['lojas'] === []): ?>
            <p>Nenhuma loja cadastrada.</p>
        <?php else: ?>
            <ul class="produtos lista-lojas">
                <?php foreach ($monitoramento['lojas'] as $loja): ?>
                    <li class="produto">
                        <h3><?= escaparMonitoramento($loja['NOME']) ?></h3>
                        <?php if ((int) $loja['ATIVA'] === 0): ?>
                            <p class="categoria">Loja inativa</p>
                        <?php endif; ?>
                        <strong><?= $loja['TIPO'] === null ? 'Sem coleta registrada' : rotuloEventoColeta($loja['TIPO']) ?></strong>
                        <?php if ($loja['DATA_EVENTO'] !== null): ?>
                            <p>Última tentativa em <?= escaparMonitoramento($loja['DATA_EVENTO']) ?></p>
                        <?php endif; ?>
                    </li>
                <?php endforeach; ?>
            </ul>
        <?php endif; ?>
    </section>
    <section class="monitoramento" aria-labelledby="eventos-recentes">
        <h2 id="eventos-recentes">Últimos eventos</h2>
        <?php if ($monitoramento['eventos'] === []): ?>
            <p>Nenhum evento de coleta registrado.</p>
        <?php else: ?>
            <div class="tabela-eventos" tabindex="0" role="region" aria-labelledby="eventos-recentes">
                <table aria-labelledby="eventos-recentes">
                    <thead><tr>
                        <th scope="col">Data e hora</th><th scope="col">Loja</th>
                        <th scope="col">Evento</th><th scope="col">Produto</th>
                    </tr></thead>
                    <tbody>
                        <?php foreach ($monitoramento['eventos'] as $evento): ?>
                            <tr>
                                <td><?= escaparMonitoramento($evento['DATA_EVENTO']) ?></td>
                                <td><?= escaparMonitoramento($evento['LOJA']) ?></td>
                                <td><?= rotuloEventoColeta($evento['TIPO']) ?></td>
                                <td><?= escaparMonitoramento($evento['PRODUTO'] ?? '—') ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
        <?php if ($paginaEventos > 1 || $monitoramento['maisEventos']): ?>
            <nav aria-label="Páginas de eventos">
                <?php if ($paginaEventos > 1): ?>
                    <a href="/painel?eventos=<?= $paginaEventos - 1 ?>#eventos-recentes">Eventos mais recentes</a>
                <?php endif; ?>
                <?php if ($monitoramento['maisEventos']): ?>
                    <a href="/painel?eventos=<?= $paginaEventos + 1 ?>#eventos-recentes">Eventos anteriores</a>
                <?php endif; ?>
            </nav>
        <?php endif; ?>
    </section>
<?php endif; ?>
