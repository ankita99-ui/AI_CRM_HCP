export const isChatEditIntent = (content: string) =>
  /(?:change|update|edit|modify|follow[- ]?up date|add to the interaction|also mention|change the name|change name|wrong doctor|why dr|not dr)/i.test(
    content,
  );

export const isChatSearchIntent = (content: string) =>
  /(?:search hcp|find doctor|find hcp|search doctor)/i.test(content);
