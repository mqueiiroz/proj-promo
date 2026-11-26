<?php
declare(strict_types=1);

function urlProduto(string $id, string $nome): string
{
    $nome = preg_replace(
        ['/[áàâãä]/iu', '/[éèêë]/iu', '/[íìîï]/iu', '/[óòôõö]/iu', '/[úùûü]/iu', '/ç/iu', '/ñ/iu'],
        ['a', 'e', 'i', 'o', 'u', 'c', 'n'],
        $nome
    );
    $slug = trim(substr(preg_replace('/[^a-z0-9]+/', '-', strtolower($nome)), 0, 100), '-');
    return '/produto/' . $id . '/' . ($slug === '' ? 'oferta' : $slug);
}
