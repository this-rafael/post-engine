import path from 'node:path';
import { pathToFileURL } from 'node:url';

const slideMarkRoot = process.argv[2];

if (!slideMarkRoot) {
  throw new Error('SlideMark root is required.');
}

const importFromSlideMark = (relativePath: string) =>
  import(pathToFileURL(path.join(slideMarkRoot, relativePath)).href);

const reactModule = await importFromSlideMark('node_modules/react/index.js');
const React = reactModule.default ?? reactModule;
// SlideMark uses the classic JSX runtime in its source files.
(globalThis as typeof globalThis & { React: typeof React }).React = React;

const { createElement } = reactModule;
const { renderToStaticMarkup } = await importFromSlideMark(
  'node_modules/react-dom/server.node.js',
);
const { safeParseSlideMarkDocument } = await importFromSlideMark(
  'src/core/schema/slidemark.schema.ts',
);
const { SlideRenderer } = await importFromSlideMark(
  'src/core/renderer/SlideRenderer.tsx',
);

let inputText = '';
for await (const chunk of process.stdin) {
  inputText += chunk;
}
const input = JSON.parse(inputText);
const parsed = safeParseSlideMarkDocument(input);

if (!parsed.success) {
  process.stdout.write(JSON.stringify({ success: false, errors: parsed.errors }));
  process.exitCode = 1;
} else {
  const rendered = parsed.data.slides.map((slide: { type: string }, slideIndex: number) => ({
    type: slide.type,
    htmlLength: renderToStaticMarkup(
      createElement(SlideRenderer, {
        document: parsed.data,
        slideIndex,
        themeId: parsed.data.theme,
      }),
    ).length,
  }));
  process.stdout.write(JSON.stringify({ success: true, rendered }));
}
