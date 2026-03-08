import React from "react";

export default function LegacyEmbedPage({ src, title, detail }) {
  const standaloneUrl = src.replace("?embed=1", "").replace("&embed=1", "");

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Legacy workspace</div>
          <h2>{title}</h2>
          <p>{detail}</p>
        </div>
        <div className="rp-header-card">
          <span>Mode</span>
          <strong>Embedded</strong>
          <small>Kept live while the React migration continues.</small>
          <a className="rp-button rp-button-secondary" href={standaloneUrl}>
            Open standalone page
          </a>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-embed-frame-wrap">
          <iframe className="rp-embed-frame" src={src} title={title} />
        </div>
      </section>
    </div>
  );
}
