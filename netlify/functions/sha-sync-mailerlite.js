/**
 * SHA → MailerLite sync
 * Receives the visitor's accumulated tracking score once an email has been
 * captured on the site, and upserts it into MailerLite as custom fields +
 * a group/tag so you can segment "hot" leads inside MailerLite the same
 * way the Tie doc describes Klaviyo segmentation.
 *
 * DEPLOY
 * Save this file at: netlify/functions/sha-sync-mailerlite.js in your
 * smarterhustleacademy-website repo (create the netlify/functions folder
 * if it doesn't exist — Netlify auto-detects it, no config needed).
 *
 * ENV VARS (set in Netlify dashboard → Site settings → Environment variables)
 *   MAILERLITE_API_KEY   — your MailerLite API key (never put this in
 *                           client-side JS — that's the whole reason this
 *                           function exists)
 *
 * MAILERLITE SETUP (one-time, in MailerLite dashboard)
 * Create these custom fields under Subscribers → Fields:
 *   sha_intent_score   (number)
 *   sha_is_hot         (text — "yes"/"no")
 *   sha_visit_count    (number)
 *   sha_products_viewed (text)
 *   sha_last_page      (text)
 */

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  var apiKey = process.env.MAILERLITE_API_KEY;
  if (!apiKey) {
    return { statusCode: 500, body: JSON.stringify({ error: "MAILERLITE_API_KEY not configured" }) };
  }

  var data;
  try {
    data = JSON.parse(event.body || "{}");
  } catch (e) {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON" }) };
  }

  if (!data.email || typeof data.email !== "string") {
    return { statusCode: 400, body: JSON.stringify({ error: "email is required" }) };
  }

  var subscriberPayload = {
    email: data.email,
    fields: {
      sha_intent_score: Number(data.score) || 0,
      sha_is_hot: data.isHot ? "yes" : "no",
      sha_visit_count: Number(data.visits) || 0,
      sha_products_viewed: Array.isArray(data.productsViewed) ? data.productsViewed.join(", ") : "",
      sha_last_page: typeof data.lastPage === "string" ? data.lastPage : ""
    }
  };

  try {
    var response = await fetch("https://connect.mailerlite.com/api/subscribers", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: "Bearer " + apiKey
      },
      body: JSON.stringify(subscriberPayload)
    });

    var result = await response.json();

    if (!response.ok) {
      return {
        statusCode: response.status,
        body: JSON.stringify({ error: "MailerLite API error", detail: result })
      };
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true })
    };
  } catch (err) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Sync failed", detail: String(err) })
    };
  }
};
