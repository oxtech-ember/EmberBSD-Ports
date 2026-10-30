import {html, render, repeat, CrLitElement} from './lit.rollup.js';
class FixtureElement extends CrLitElement {
  static get properties() { return {someValue: {type: String}}; }
  constructor() { super(); this.someValue = 'initial'; }
  render() { return html`<span>${this.someValue}</span>`; }
}
customElements.define('fixture-lit-element', FixtureElement);
const component = document.createElement('fixture-lit-element');
component.setAttribute('some-value', 'ready');
document.body.append(component);
await component.updateComplete;
const container = document.createElement('main');
document.body.append(container);
render(html`<ul>${repeat(['one', 'two'], (v) => v, (v) => html`<li>${v}</li>`)}</ul>`, container);
let blocked = false;
try { trustedTypes.createPolicy('not-allowed', {createHTML: value => value}); }
catch (error) { blocked = error instanceof TypeError; }
const items = [...container.querySelectorAll('li')].map(node => node.textContent);
document.body.dataset.result = JSON.stringify({items, blocked, property: component.someValue, shadow: component.shadowRoot.textContent.trim()});
