import pandas as pd
import os

golden_path = os.path.join(os.path.dirname(__file__), '../eval/golden_set.csv')
df = pd.read_csv(golden_path)

# Type A: Genuine Safety Incidents mislabeled as auto_handle -> fix to escalate
type_a_ids = [2728, 414646, 590098, 527787, 417056, 598480, 332892, 304648]
df.loc[df['tweet_id'].isin(type_a_ids), 'true_escalation_decision'] = 'escalate'

# Type B: Not safety incidents at all -> Fix intent, and set escalation based on intent's standard rule
fixes_b = {
    564439: ('lost_item', 'auto_handle'),
    583039: ('lost_item', 'auto_handle'),
    122401: ('account_access_issue', 'escalate'),
    59667:  ('account_access_issue', 'escalate'),
    515383: ('app_technical_bug', 'auto_handle'),
    515376: ('driver_behavior_complaint', 'escalate'),
    41715:  ('general_inquiry', 'auto_handle'),
    474442: ('app_technical_bug', 'auto_handle'),
    219891: ('driver_behavior_complaint', 'escalate')
}

for tw_id, (intent, esc) in fixes_b.items():
    df.loc[df['tweet_id'] == tw_id, 'true_intent'] = intent
    df.loc[df['tweet_id'] == tw_id, 'true_escalation_decision'] = esc

# Overwrite dataset
df.to_csv(golden_path, index=False)
print("Finished rewriting eval/golden_set.csv. Contradictions fixed.")
