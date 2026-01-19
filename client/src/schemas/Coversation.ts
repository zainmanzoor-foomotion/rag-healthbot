import mongoose, { Schema, Document } from 'mongoose';


export interface IMessage {
  userContent?: string;
  aiContent?: string;
}

export interface IConversation extends Document {
  title: string;
  messages: IMessage[];
  metadata?: Record<string, unknown>;
}


const MessageSchema = new Schema<IMessage>({
  userContent: {
    type: String,
    required: false
  },
  aiContent: {
    type: String,
    required: false,
  }
});

const ConversationSchema = new Schema<IConversation>({
  title: {
    type: String,
    required: true,
    default: 'New Conversation',
  },
  messages: [MessageSchema],
  metadata: {
    type: Schema.Types.Mixed,
    required: false,
    default: {},
  },
}, {
  timestamps: true,
});

export default mongoose.models.Conversation ||
  mongoose.model<IConversation>("Conversation", ConversationSchema);