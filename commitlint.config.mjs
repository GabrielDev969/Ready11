export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Types permitidos
    'type-enum': [
      2,
      'always',
      [
        'feat',     // nova funcionalidade
        'fix',      // correção de bug
        'docs',     // apenas documentação
        'style',    // formatação, ponto e vírgula, etc. (sem mudança de lógica)
        'refactor', // refatoração sem nova feature ou fix
        'test',     // adição ou correção de testes
        'chore',    // manutenção (deps, build, config)
        'perf',     // melhoria de performance
        'ci',       // mudanças de CI/CD
        'build',    // mudanças no sistema de build
        'revert',   // reverter commit anterior
      ],
    ],
    'subject-case': [0],           // não força capitalização do subject
    'header-max-length': [2, 'always', 100],
  },
};
