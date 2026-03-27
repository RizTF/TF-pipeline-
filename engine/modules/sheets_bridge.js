#!/usr/bin/env node
/**
 * Google Sheets bridge — called by Python via subprocess.
 * Uses the same credentials as Scout (Node.js can parse the key, Python can't).
 *
 * Usage:
 *   node sheets_bridge.js test
 *   node sheets_bridge.js log '["2024-01-01","from@x.com","Name","Co","Subject","POSITIVE","Summary","high","auto-reply","0.95"]'
 */

const {google} = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDS_FILE = process.env.GOOGLE_CREDENTIALS_FILE || path.join(__dirname, '..', 'config', 'google_credentials.json');
const SHEET_ID = process.env.GOOGLE_SHEETS_ID;
const SHEET_NAME = 'Employer Replies';

async function getSheets() {
    const creds = JSON.parse(fs.readFileSync(CREDS_FILE, 'utf8'));
    const auth = new google.auth.GoogleAuth({
        credentials: creds,
        scopes: ['https://www.googleapis.com/auth/spreadsheets'],
    });
    return google.sheets({version: 'v4', auth: await auth.getClient()});
}

async function ensureSheet(sheets) {
    try {
        await sheets.spreadsheets.values.get({
            spreadsheetId: SHEET_ID,
            range: `'${SHEET_NAME}'!A1`,
        });
    } catch (e) {
        if (e.code === 400 || (e.message && e.message.includes('Unable to parse range'))) {
            await sheets.spreadsheets.batchUpdate({
                spreadsheetId: SHEET_ID,
                requestBody: {
                    requests: [{addSheet: {properties: {title: SHEET_NAME}}}],
                },
            });
            await sheets.spreadsheets.values.update({
                spreadsheetId: SHEET_ID,
                range: `'${SHEET_NAME}'!A1:J1`,
                valueInputOption: 'RAW',
                requestBody: {
                    values: [['Timestamp', 'From', 'Name', 'Company', 'Subject', 'Category', 'Summary', 'Urgency', 'Action Taken', 'Confidence']],
                },
            });
        }
    }
}

async function main() {
    const cmd = process.argv[2];

    if (cmd === 'test') {
        try {
            const sheets = await getSheets();
            const res = await sheets.spreadsheets.values.get({
                spreadsheetId: SHEET_ID,
                range: `'${SHEET_NAME}'!A1`,
            });
            console.log(JSON.stringify({ok: true}));
        } catch (e) {
            // Sheet might not exist yet, try creating it
            try {
                const sheets = await getSheets();
                await ensureSheet(sheets);
                console.log(JSON.stringify({ok: true}));
            } catch (e2) {
                console.log(JSON.stringify({ok: false, error: e2.message}));
            }
        }
    } else if (cmd === 'log') {
        const row = JSON.parse(process.argv[3]);
        try {
            const sheets = await getSheets();
            await ensureSheet(sheets);
            await sheets.spreadsheets.values.append({
                spreadsheetId: SHEET_ID,
                range: `'${SHEET_NAME}'!A:J`,
                valueInputOption: 'USER_ENTERED',
                requestBody: {values: [row]},
            });
            console.log(JSON.stringify({ok: true}));
        } catch (e) {
            console.log(JSON.stringify({ok: false, error: e.message}));
        }
    } else {
        console.log(JSON.stringify({ok: false, error: 'Usage: node sheets_bridge.js test|log'}));
    }
}

main();
