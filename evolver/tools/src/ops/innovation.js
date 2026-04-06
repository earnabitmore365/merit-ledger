// Innovation Catalyst (v1.0) - Evolver Core Module
// Analyzes system state to propose concrete innovation ideas when stagnation is detected.

const fs = require('fs');
const path = require('path');
const { getSkillsDir } = require('../gep/paths');

function listSkills() {
    try {
        const dir = getSkillsDir();
        if (!fs.existsSync(dir)) return [];
        return fs.readdirSync(dir).filter(f => !f.startsWith('.'));
    } catch (e) { return []; }
}

function generateInnovationIdeas() {
    const skills = listSkills();
    const skillSet = new Set(skills.map(s => s.toLowerCase()));

    // Check if a skill name (or close variant) already exists
    function skillExists(name) {
        var n = name.toLowerCase();
        return skillSet.has(n) || skills.some(s => s.toLowerCase().includes(n) || n.includes(s.toLowerCase()));
    }

    const categories = {
        'feishu': skills.filter(s => s.startsWith('feishu-')).length,
        'dev': skills.filter(s => s.startsWith('git-') || s.startsWith('code-') || s.includes('lint') || s.includes('test') || s.includes('todo')).length,
        'media': skills.filter(s => s.includes('image') || s.includes('video') || s.includes('music') || s.includes('voice')).length,
        'security': skills.filter(s => s.includes('security') || s.includes('audit') || s.includes('guard') || s.includes('secret')).length,
        'automation': skills.filter(s => s.includes('auto-') || s.includes('scheduler') || s.includes('cron')).length,
        'data': skills.filter(s => s.includes('db') || s.includes('store') || s.includes('cache') || s.includes('index')).length,
        'meta': skills.filter(s => s.includes('evo-') || s.includes('evolution') || s.includes('gene-') || s.includes('capsule')).length
    };

    // Find under-represented categories
    const sortedCats = Object.entries(categories).sort((a, b) => a[1] - b[1]);
    const weakAreas = sortedCats.slice(0, 2).map(c => c[0]);

    // Candidate ideas pool — each with a guard skill name to check existence
    const candidatePool = [
        { area: 'security', guard: 'dependency-scanner', text: "- Security: Implement a 'dependency-scanner' skill to check for vulnerable packages." },
        { area: 'security', guard: 'permission-auditor', text: "- Security: Create a 'permission-auditor' to review tool usage patterns." },
        { area: 'media', guard: 'meme-generator', text: "- Media: Add a 'meme-generator' skill for social engagement." },
        { area: 'media', guard: 'video-summarizer', text: "- Media: Create a 'video-summarizer' using ffmpeg keyframes." },
        { area: 'dev', guard: 'code-stats', text: "- Dev: Build a 'code-stats' skill to visualize repo complexity." },
        { area: 'dev', guard: 'todo-manager', text: "- Dev: Implement a 'todo-manager' that syncs code TODOs to tasks." },
        { area: 'dev', guard: 'test-runner', text: "- Dev: Create a 'test-runner' skill to auto-execute and report test suites." },
        { area: 'automation', guard: 'meeting-prep', text: "- Automation: Create a 'meeting-prep' skill that auto-summarizes calendar context." },
        { area: 'automation', guard: 'broken-link-checker', text: "- Automation: Build a 'broken-link-checker' for documentation." },
        { area: 'data', guard: 'local-vector-store', text: "- Data: Implement a 'local-vector-store' for semantic search." },
        { area: 'data', guard: 'log-analyzer', text: "- Data: Create a 'log-analyzer' to visualize system health trends." },
        { area: 'meta', guard: 'performance-metric', text: "- Meta: Enhance the Evolver's self-reflection by adding a 'performance-metric' dashboard." }
    ];

    const ideas = candidatePool.filter(c =>
        weakAreas.includes(c.area) && !skillExists(c.guard)
    ).map(c => c.text);

    // Optimization ideas (only if large skill set)
    if (skills.length > 50) {
        ideas.push("- Optimization: Identify and deprecate unused skills (e.g., redundant search tools).");
    }

    return ideas.slice(0, 3);
}

module.exports = { generateInnovationIdeas };
