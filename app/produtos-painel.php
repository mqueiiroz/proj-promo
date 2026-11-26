<?php
$nomesCategorias = [
    'COOLER' => 'Air coolers', 'CPU' => 'Processadores', 'FONTE' => 'Fontes de alimentação',
    'GABINETE' => 'Gabinetes', 'GPU' => 'Placas de vídeo', 'HD' => 'HDs', 'PLACA_MAE' => 'Placas-mãe',
    'RAM' => 'Memórias RAM', 'SSD' => 'SSDs', 'WATER_COOLER' => 'Water coolers',
];
?>
<?php if ($catalogo === null): ?>
    <p role="alert">Não foi possível carregar o catálogo agora.</p>
<?php elseif ($catalogo === []): ?>
    <p>Nenhum produto cadastrado.</p>
<?php else: ?>
    <?php foreach ($catalogo as $categoria => $produtos): ?>
        <?php $rotulo = escaparMonitoramento($nomesCategorias[$categoria] ?? (string) $categoria); ?>
        <details class="painel-claro catalogo-categoria">
            <summary><strong><?= $rotulo ?></strong> (<?= count($produtos) ?>)</summary>
            <div class="tabela-eventos tabela-gestao" tabindex="0" role="region" aria-label="Produtos de <?= $rotulo ?>">
                <table aria-label="Produtos de <?= $rotulo ?>">
                    <thead><tr><th scope="col">Produto</th><th scope="col">Loja</th><th scope="col">Promoção</th></tr></thead>
                    <tbody>
                        <?php foreach ($produtos as $produto): ?>
                            <tr>
                                <td><a class="acao-secundaria" href="<?= urlProduto((string) $produto['ID'], $produto['NOME']) ?>"><?= escaparMonitoramento($produto['NOME']) ?></a></td>
                                <td><?= escaparMonitoramento($produto['LOJA']) ?></td>
                                <td><?= (int) $produto['EM_PROMOCAO'] === 1 ? 'Em promoção' : 'Não está em promoção' ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </details>
    <?php endforeach; ?>
<?php endif; ?>
