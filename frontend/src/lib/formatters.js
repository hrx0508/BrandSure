export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '')
export const STATUS_LABEL = { draft: 'Draft', in_review: 'With reviewer', changes_requested: 'Changes requested', approved: 'Approved', published: 'Published', rejected: 'Rejected' }
export const KIT_STATE_LABEL = { needs_confirmation: 'Needs confirmation', ready_to_send: 'Ready to send', live: 'Live for creators', inactive: 'Inactive' }
export const EVIDENCE_LABEL = {
  approved_rule: 'Matches an approved rule', reviewer: 'Added by a human reviewer', verified: 'Verified against approved source', not_found: 'No supporting source found',
  invalid_citation: 'Citation not in this kit', quote_invalid: 'Quoted text not found in source', weak_support: 'Source does not clearly support this',
}
export const VERDICT_LABEL = { supported: 'Supported', contradicted: 'Contradicted', unverified: 'Unverified' }
export const TYPE_LABEL = {
  terminology: 'Preferred term', banned_term: 'Banned term', expired_offer: 'Expired offer', date_conflict: 'Date conflict',
  missing_disclaimer: 'Missing disclaimer', unsupported_claim: 'Claim', tone_mismatch: 'Tone', visual_palette: 'Colour palette',
  missing_alt: 'Alt text', reviewer_suggestion: 'Reviewer suggestion', low_contrast: 'Contrast', other: 'Other',
}
export const RULE_LABEL = {
  preferred_term: 'Preferred term', banned_term: 'Banned term', expiry: 'Offer validity', required_disclaimer: 'Required disclaimer',
  claim_rule: 'Claim rule', tone_guideline: 'Tone guidance', fact: 'Approved fact', palette: 'Colour palette', accessibility: 'Accessibility',
}
export const AUDIT_LABEL = {
  'kit.extracted': 'Guidelines extracted', 'kit.confirmed': 'Brand Kit confirmed', 'review.created': 'Review created',
  'review.analyzed': 'Reviewer started the review', 'review.revised': 'New version saved', 'review.requested': 'Submitted to reviewer',
  'review.approved': 'Approved', 'review.changes_requested': 'Sent back with flags', 'image.attached': 'Image attached',
  'finding.accepted': 'Finding accepted', 'finding.edited': 'Finding edited', 'finding.dismissed': 'Reviewer dismissed a finding', 'finding.flagged': 'Reviewer flagged a finding',
  'finding.resolved': 'Finding resolved', 'finding.open': 'Finding reopened', 'kit.published': 'Brand Kit sent to creators',
  'kit.deactivated': 'Brand Kit deactivated', 'kit.activated': 'Brand Kit activated', 'kit.deleted': 'Brand Kit deleted',
  'review.rejected': 'Rejected', 'review.published': 'Marked as published', 'review.suggested': 'Reviewer added a suggestion',
  'review.edited_by_reviewer': 'Reviewer edited the post',
}
export const statusLabel = (status, role) => (role === 'creator' && status === 'in_review' ? 'Submitted' : role === 'reviewer' && status === 'in_review' ? 'To review' : STATUS_LABEL[status] || status)
export const FLAG_STATUS = { open: 'Not triaged', flagged: 'Needs your fix', accepted: 'Accepted', edited: 'Edited', resolved: 'Fixed', dismissed: 'Dismissed' }
export const ROLE_LABEL = { admin: 'Brand Admin', creator: 'Creator', reviewer: 'Reviewer' }
