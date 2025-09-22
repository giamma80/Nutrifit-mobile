module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'body-max-line-length': [2, 'always', 120],
    // Prefisso componente opzionale prima del type: es: backend: feat(...)
    'header-pattern': [2, 'always', /^(?:((backend|mobile|web|repo)):\s)?(feat|fix|docs|chore|refactor|perf|test|build|ci|style)(?:\(([^)]+)\))?: .+$/],
    'header-max-length': [2, 'always', 100]
  }
};
